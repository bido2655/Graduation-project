/**
 * NEXUS PRO EDITOR - Core Logic
 */

let diagramModel = { entities: [], relationships: [] };
let selectedElementId = null;
let isPanning = false;
let currentZoom = 1.0;
let panX = 0;
let panY = 0;
let dragStartX, dragStartY;

const seqDropTypes = ['participant', 'database', 'boundary', 'control', 'entity', 'activation', 'alt', 'loop'];
const seqTypes = ['participant', 'database', 'boundary', 'control', 'entity', 'activation'];
const bpmnTypes = ['bpmn-task', 'bpmn-gateway', 'bpmn-start', 'bpmn-end'];
const activityTypes = ['activity-action', 'activity-decision', 'activity-initial', 'activity-final'];
const specialShapes = [...seqTypes, ...bpmnTypes, ...activityTypes, 'alt', 'loop', 'actor', 'usecase', 'interface', 'table'];
let undoStack = [];
let redoStack = [];
const MAX_HISTORY = 50;

const canvasContainer = document.getElementById('canvas-container');
const canvasContent = document.getElementById('canvas-content');
const connectionsLayer = document.getElementById('connections-layer');
const zoomLevelText = document.getElementById('zoomLevel');

// Track DOM elements for performance
const nodeElements = new Map();
const relationshipElements = new Map();


// Initialize
window.addEventListener('DOMContentLoaded', () => {
    loadModel();
    initAccordion();
    initZoomControls();
    initPanControls();
    initCanvasEvents();
    renderAll();

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
        const isCtrl = e.ctrlKey || e.metaKey;

        // Undo: Ctrl+Z
        if (isCtrl && e.key === 'z' && !e.shiftKey) {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            e.preventDefault();
            undo();
        }
        // Redo: Ctrl+Y or Ctrl+Shift+Z
        if (isCtrl && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            e.preventDefault();
            redo();
        }

        if (e.key === 'Delete' || e.key === 'Backspace') {
            if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) return;
            if (selectedElementId) {
                pushToHistory();
                deleteSelected();
            }
        }
    });

    // Toolbar Undo/Redo
    document.getElementById('undoBtn').onclick = undo;
    document.getElementById('redoBtn').onclick = redo;
});

// --- State Management ---
function loadModel() {
    const saved = localStorage.getItem('nexus_current_model');
    if (saved) {
        try {
            diagramModel = JSON.parse(saved);
            // Normalize from/to -> from_id/to_id if needed
            diagramModel.relationships.forEach(rel => {
                if (rel.from && !rel.from_id) rel.from_id = rel.from;
                if (rel.to && !rel.to_id) rel.to_id = rel.to;
            });

            // CRITICAL FIX: Filter out orphaned relationships that reference non-existent entities
            const entityIds = new Set(diagramModel.entities.map(e => e.id));
            const validRelationships = diagramModel.relationships.filter(rel => {
                const fromExists = entityIds.has(rel.from_id);
                const toExists = entityIds.has(rel.to_id);
                if (!fromExists || !toExists) {
                    console.warn(`Removing orphaned relationship: ${rel.from_id} -> ${rel.to_id} (entities missing)`);
                    return false;
                }
                return true;
            });
            diagramModel.relationships = validRelationships;

            // Auto-layout for nodes that overlap or have no position
            let gridX = 50, gridY = 50;
            diagramModel.entities.forEach(node => {
                if ((!node.x && !node.y) || (node.x === 0 && node.y === 0)) {
                    node.x = gridX;
                    node.y = gridY;
                    gridX += 250;
                    if (gridX > 1000) {
                        gridX = 50;
                        gridY += 200;
                    }
                }
                if (!node.width) node.width = 180;
                if (!node.height) node.height = 120;
            });
        } catch (e) {
            console.error('Failed to parse model', e);
        }
    }
}

function saveModel() {
    localStorage.setItem('nexus_current_model', JSON.stringify(diagramModel));
}

function pushToHistory() {
    // Clone model and push to undoStack
    undoStack.push(JSON.parse(JSON.stringify(diagramModel)));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack = []; // Clear redo stack on new action
}

function undo() {
    if (undoStack.length === 0) return;

    // Push current to redo
    redoStack.push(JSON.parse(JSON.stringify(diagramModel)));
    if (redoStack.length > MAX_HISTORY) redoStack.shift();

    // Restore from undo
    diagramModel = undoStack.pop();
    saveModel();
    renderAll();
    selectElement(null);
}

function redo() {
    if (redoStack.length === 0) return;

    // Push current to undo
    undoStack.push(JSON.parse(JSON.stringify(diagramModel)));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();

    // Restore from redo
    diagramModel = redoStack.pop();
    saveModel();
    renderAll();
    selectElement(null);
}

// --- Rendering ---
function renderAll() {
    renderNodes();
    renderConnections();
    updatePropertyPanel();
}

function renderNodes() {
    // Surgically remove only nodes to preserve the SVG layer
    canvasContent.querySelectorAll('.editor-node').forEach(n => n.remove());
    nodeElements.clear();
    diagramModel.entities.forEach(entity => {
        const el = createNodeElement(entity);
        canvasContent.appendChild(el);
        nodeElements.set(entity.id, el);
    });
}

function createNodeElement(entity) {
    const node = document.createElement('div');
    node.className = `editor-node ${selectedElementId === entity.id ? 'selected' : ''}`;
    node.style.left = `${entity.x}px`;
    node.style.top = `${entity.y}px`;
    if (entity.width) node.style.width = `${entity.width}px`;
    if (entity.height) node.style.height = `${entity.height}px`;
    node.dataset.id = entity.id;

    let typeLabel = '';
    let bodyContent = `
        <div class="attributes border-b border-white/5 pb-1 mb-1">
            ${entity.attributes.map(a => `<div class="truncate">• ${a}</div>`).join('')}
        </div>
        <div class="methods">
            ${entity.methods.map(m => `<div class="truncate text-indigo-300">ƒ ${m}</div>`).join('')}
        </div>
    `;

    // Check if this is a sequence diagram type
    const isSeqType = seqTypes.includes(entity.type);

    if (entity.type === 'interface') typeLabel = '«interface»';
    else if (entity.type === 'actor') {
        node.style.background = 'rgba(255, 255, 255, 0.001)';
        node.style.border = 'none';
        node.style.boxShadow = 'none';
        if (!entity.width) entity.width = 60;
        if (!entity.height) entity.height = 90;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `
            <div class="flex flex-col items-center w-full h-full justify-center">
                <svg viewBox="0 0 24 40" fill="none" stroke="currentColor" stroke-width="1.5" class="w-full h-full max-w-[60%] max-h-[80%] text-indigo-400">
                    <circle cx="12" cy="8" r="5" fill="#fef3c7" stroke="#92400e"/>
                    <path d="M12 13v12M5 18h14M12 25l-5 10M12 25l5 10" stroke="#475569" stroke-width="2"/>
                </svg>
                <div class="mt-1 text-[11px] font-bold text-center truncate w-full px-2">${entity.name}</div>
            </div>
        `;
    } else if (entity.type === 'activation') {
        node.style.background = 'transparent';
        node.style.border = 'none';
        node.style.boxShadow = 'none';
        if (!entity.width) entity.width = 30;
        if (!entity.height) entity.height = 200;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `
            <div class="draggable-shape" style="display:flex;flex-direction:column;align-items:center;width:100%;height:100%;position:relative;cursor:grab;">
                <!-- Expanding the transparent space to make the bar easier to drag -->
                <div style="position:absolute;top:10%;bottom:10%;width:12px;background:#f8fafc;border:2px solid #475569;border-radius:2px;z-index:2;box-shadow:0 4px 12px rgba(0,0,0,0.15);display:flex;flex-direction:column;">
                    <div class="activation-drag-handle draggable-shape" style="width:100%;height:12px;background:#cbd5e1;cursor:grab;display:flex;align-items:center;justify-content:center;border-bottom:1px solid #94a3b8;" title="Drag to move bar">
                        <div style="width:8px;height:2px;border-top:1.5px solid #64748b;border-bottom:1.5px solid #64748b;pointer-events:none;"></div>
                    </div>
                    <div class="lifeline-hit-area" style="width:100%;flex-grow:1;cursor:crosshair;" title="Click and drag to draw arrow"></div>
                </div>
            </div>
            <style>
                .lifeline-hit-area:hover {
                    background: rgba(129, 140, 248, 0.1);
                }
            </style>
        `;
    } else if (entity.type === 'alt' || entity.type === 'loop') {
        node.style.background = 'transparent';
        node.style.pointerEvents = 'none'; // Allow clicks to pass through to elements underneath
        if (!entity.width) entity.width = 200;
        if (!entity.height) entity.height = 150;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        node.style.border = 'none';
        bodyContent = `
            <div style="position:absolute;inset:0;border:2px solid #4f46e5;pointer-events:none;z-index:1;"></div>
            <div style="position:absolute;top:0;left:0;right:0;height:6px;pointer-events:auto;cursor:grab;z-index:5;" class="draggable-shape"></div>
            <div style="position:absolute;bottom:0;left:0;right:0;height:6px;pointer-events:auto;cursor:grab;z-index:5;" class="draggable-shape"></div>
            <div style="position:absolute;top:0;bottom:0;left:0;width:6px;pointer-events:auto;cursor:grab;z-index:5;" class="draggable-shape"></div>
            <div style="position:absolute;top:0;bottom:0;right:0;width:6px;pointer-events:auto;cursor:grab;z-index:5;" class="draggable-shape"></div>
            <div class="draggable-shape" style="position:absolute;top:0;left:0;height:24px;background:transparent;border-right:2px solid #4f46e5;border-bottom:2px solid #4f46e5;color:#4f46e5;padding:0 8px;font-size:12px;font-weight:bold;display:flex;align-items:center;z-index:2;border-bottom-right-radius:4px;pointer-events:auto;cursor:grab;">
                ${entity.type} ${entity.name ? `<span style="font-weight:normal;margin-left:6px;opacity:0.8;">[${entity.name}]</span>` : ''}
            </div>
        `;
    } else if (isSeqType) {
        node.style.background = 'transparent';
        node.style.border = 'none';
        node.style.boxShadow = 'none';
        node.style.borderRadius = '0';
        if (!entity.width) entity.width = 100;
        if (!entity.height) entity.height = 300;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;

        let seqIcon = '';
        let headerBg = '#3b82f6';
        let headerBorder = '#1e40af';

        if (entity.type === 'participant') seqIcon = '';
        else if (entity.type === 'database') {
            headerBg = '#0f766e';
            headerBorder = '#064e3b';
            seqIcon = `<svg viewBox="0 0 40 28" fill="none" stroke="#e2e8f0" stroke-width="1.5" style="width:40px;height:28px;margin:0 auto 4px auto;display:block;">
                <ellipse cx="20" cy="6" rx="14" ry="5" fill="${headerBg}" stroke="${headerBorder}"/>
                <path d="M6 6v16c0 2.76 6.27 5 14 5s14-2.24 14-5V6" fill="${headerBg}" stroke="${headerBorder}"/>
                <ellipse cx="20" cy="22" rx="14" ry="5" fill="none" stroke="${headerBorder}"/>
            </svg>`;
        } else if (entity.type === 'boundary') {
            headerBg = '#7c3aed';
            headerBorder = '#5b21b6';
            seqIcon = `<svg viewBox="0 0 40 24" fill="none" stroke="#e2e8f0" stroke-width="1.5" style="width:36px;height:24px;margin:0 auto 4px auto;display:block;">
                <line x1="6" y1="2" x2="6" y2="22"/><line x1="6" y1="12" x2="13" y2="12"/><circle cx="25" cy="12" r="10" fill="none"/>
            </svg>`;
        } else if (entity.type === 'control') {
            headerBg = '#0369a1';
            headerBorder = '#075985';
            seqIcon = `<svg viewBox="0 0 40 28" fill="none" stroke="#e2e8f0" stroke-width="1.5" style="width:36px;height:28px;margin:0 auto 4px auto;display:block;">
                <circle cx="20" cy="16" r="10" fill="none"/><path d="M16 4 L20 8 L24 4"/>
            </svg>`;
        } else if (entity.type === 'entity') {
            headerBg = '#b45309';
            headerBorder = '#92400e';
            seqIcon = `<svg viewBox="0 0 40 28" fill="none" stroke="#e2e8f0" stroke-width="1.5" style="width:36px;height:28px;margin:0 auto 4px auto;display:block;">
                <circle cx="20" cy="12" r="10" fill="none"/><line x1="8" y1="24" x2="32" y2="24" stroke-width="2"/>
            </svg>`;
        }

        bodyContent = `
            <div style="display:flex;flex-direction:column;align-items:center;width:100%;height:100%;gap:0;">
                ${seqIcon}
                <div style="background:${headerBg};border:2px solid ${headerBorder};border-radius:4px;padding:6px 14px;font-weight:bold;font-size:12px;color:#f8fafc;text-align:center;white-space:nowrap;min-width:60px;cursor:move;">${entity.name}</div>
                <div class="lifeline-hit-area" style="flex:1;width:24px;display:flex;justify-content:center;cursor:crosshair;z-index:5;">
                    <div class="lifeline-visible-line" style="height:100%;width:0;border-left:2px dashed #475569;transition:border-color 0.2s;"></div>
                </div>
                <style>
                    .lifeline-hit-area:hover .lifeline-visible-line {
                        border-left-color: #818cf8 !important;
                        border-left-style: solid !important;
                    }
                </style>
                <div style="background:${headerBg};border:2px solid ${headerBorder};border-radius:4px;padding:6px 14px;font-weight:bold;font-size:12px;color:#f8fafc;text-align:center;white-space:nowrap;min-width:60px;">${entity.name}</div>
            </div>
        `;
    } else if (entity.type === 'usecase') {
        node.style.borderRadius = '50% / 100%';
        node.style.height = '80px';
        bodyContent = '';
    } else if (entity.type === 'table') {
        typeLabel = '«table»';
    } else if (entity.type === 'bpmn-task') {
        node.style.borderRadius = '10px';
        bodyContent = `<div class="flex items-center justify-center h-full text-center font-semibold px-2">${entity.name}</div>`;
    } else if (entity.type === 'bpmn-gateway') {
        node.style.background = 'transparent';
        node.style.border = 'none';
        node.style.boxShadow = 'none';
        if (!entity.width) entity.width = 60;
        if (!entity.height) entity.height = 60;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `
            <svg viewBox="0 0 100 100" class="w-full h-full text-indigo-400">
                <path d="M50 5 L95 50 L50 95 L5 50 Z" fill="rgba(99,102,241,0.1)" stroke="currentColor" stroke-width="4"/>
                <path d="M50 30 L50 70 M30 50 L70 50" stroke="currentColor" stroke-width="4"/>
            </svg>
            <div class="absolute -bottom-6 left-0 right-0 text-center text-[10px] font-bold truncate">${entity.name}</div>
        `;
    } else if (entity.type === 'bpmn-start') {
        node.style.borderRadius = '50%';
        if (!entity.width) entity.width = 40;
        if (!entity.height) entity.height = 40;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `<div class="flex items-center justify-center h-full text-green-400">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="w-6 h-6"><circle cx="12" cy="12" r="10"/></svg>
        </div>`;
    } else if (entity.type === 'bpmn-end') {
        node.style.borderRadius = '50%';
        if (!entity.width) entity.width = 40;
        if (!entity.height) entity.height = 40;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `<div class="flex items-center justify-center h-full text-red-500">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="4" class="w-6 h-6"><circle cx="12" cy="12" r="10"/></svg>
        </div>`;
    } else if (entity.type === 'activity-action') {
        node.style.borderRadius = '20px';
        bodyContent = `<div class="flex items-center justify-center h-full text-center px-4">${entity.name}</div>`;
    } else if (entity.type === 'activity-decision') {
        node.style.background = 'transparent';
        node.style.border = 'none';
        node.style.boxShadow = 'none';
        if (!entity.width) entity.width = 50;
        if (!entity.height) entity.height = 50;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `
            <svg viewBox="0 0 100 100" class="w-full h-full text-indigo-400">
                <path d="M50 5 L95 50 L50 95 L5 50 Z" fill="rgba(99,102,241,0.1)" stroke="currentColor" stroke-width="4"/>
            </svg>
            <div class="absolute -top-6 left-0 right-0 text-center text-[10px] font-bold truncate">${entity.name}</div>
        `;
    } else if (entity.type === 'activity-initial') {
        node.style.borderRadius = '50%';
        node.style.background = 'var(--text-main)';
        if (!entity.width) entity.width = 25;
        if (!entity.height) entity.height = 25;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = '';
    } else if (entity.type === 'activity-final') {
        node.style.borderRadius = '50%';
        node.style.background = 'transparent';
        if (!entity.width) entity.width = 30;
        if (!entity.height) entity.height = 30;
        node.style.width = `${entity.width}px`;
        node.style.height = `${entity.height}px`;
        bodyContent = `
            <div class="flex items-center justify-center w-full h-full">
                <div style="width:100%; height:100%; border:2px solid var(--text-main); border-radius:50%; display:flex; items-center; justify-center; padding:3px;">
                    <div style="width:100%; height:100%; background:var(--text-main); border-radius:50%;"></div>
                </div>
            </div>
        `;
    }

    let headerClass = "bg-indigo-600/20";
    if (entity.type === 'interface') headerClass = "bg-purple-600/20";
    if (entity.type === 'actor') headerClass = "bg-teal-600/20";
    if (entity.type === 'usecase') headerClass = "bg-pink-600/20";
    if (entity.type === 'table') headerClass = "bg-emerald-600/20";
    if (isSeqType) headerClass = "bg-blue-600/20";
    if (bpmnTypes.includes(entity.type)) headerClass = "bg-amber-600/20";
    if (activityTypes.includes(entity.type)) headerClass = "bg-rose-600/20";

    const isArrow = entity.type === 'arrow';
    let resizeHandles = '';
    let connHandles = '';
    const arrowSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14m-7-7 7 7-7 7"/></svg>';

    if (isArrow) {
        resizeHandles = `
            <div class="node-resize-handle handle-l" data-corner="l"></div>
            <div class="node-resize-handle handle-r" data-corner="r"></div>
        `;
    } else if (isSeqType) {
        if (entity.type === 'activation') {
            resizeHandles = `
                <div class="node-resize-handle handle-t" data-corner="t" style="top:10%; margin-top:-4px; opacity:0 !important; width:100%; height:8px; border:none; background:transparent;"></div>
                <div class="node-resize-handle handle-b" data-corner="b" style="top:auto; bottom:10%; margin-bottom:-4px; opacity:0 !important; width:100%; height:8px; border:none; background:transparent;"></div>
            `;
            connHandles = '';
        } else {
            resizeHandles = `
                <div class="node-resize-handle handle-t" data-corner="t"></div>
                <div class="node-resize-handle handle-b" data-corner="b"></div>
            `;
            connHandles = `
                <div class="conn-handle" data-side="right" style="position:absolute;left:calc(50% + 2px);top:calc(50% - 15px);width:16px;height:30px;transform:none;background:transparent;">
                    <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;opacity:0.6;">
                        <svg viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:16px;"><path d="M2 2l6 6-6 6"/></svg>
                    </div>
                </div>
                <div class="conn-handle" data-side="left" style="position:absolute;left:calc(50% - 18px);top:calc(50% - 15px);width:16px;height:30px;transform:none;background:transparent;">
                    <div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;opacity:0.6;">
                        <svg viewBox="0 0 10 16" fill="none" stroke="currentColor" stroke-width="2" style="width:10px;height:16px;"><path d="M8 2l-6 6 6 6"/></svg>
                    </div>
                </div>
            `;
        }
    } else if (entity.type === 'alt' || entity.type === 'loop') {
        resizeHandles = `
            <div class="node-resize-handle handle-t" data-corner="t" style="top:-4px; left:0; right:0; width:100%; height:10px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-b" data-corner="b" style="bottom:-4px; left:0; right:0; width:100%; height:10px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-l" data-corner="l" style="left:-4px; top:0; bottom:0; width:10px; height:100%; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-r" data-corner="r" style="right:-4px; top:0; bottom:0; width:10px; height:100%; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-tl" data-corner="tl" style="top:-6px; left:-6px; width:14px; height:14px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-tr" data-corner="tr" style="top:-6px; right:-6px; width:14px; height:14px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-bl" data-corner="bl" style="bottom:-6px; left:-6px; width:14px; height:14px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
            <div class="node-resize-handle handle-br" data-corner="br" style="bottom:-6px; right:-6px; width:14px; height:14px; border:none; background:transparent; opacity:0 !important; pointer-events:auto;"></div>
        `;
        connHandles = '';
    } else {
        resizeHandles = `
            <div class="node-resize-handle handle-tl" data-corner="tl"></div>
            <div class="node-resize-handle handle-tr" data-corner="tr"></div>
            <div class="node-resize-handle handle-bl" data-corner="bl"></div>
            <div class="node-resize-handle handle-br" data-corner="br"></div>
            <div class="node-resize-handle handle-t" data-corner="t"></div>
            <div class="node-resize-handle handle-b" data-corner="b"></div>
            <div class="node-resize-handle handle-l" data-corner="l"></div>
            <div class="node-resize-handle handle-r" data-corner="r"></div>
        `;
        connHandles = `
            <div class="conn-handle handle-top" data-side="top">${arrowSvg}</div>
            <div class="conn-handle handle-right" data-side="right">${arrowSvg}</div>
            <div class="conn-handle handle-bottom" data-side="bottom">${arrowSvg}</div>
            <div class="conn-handle handle-left" data-side="left">${arrowSvg}</div>
        `;
    }

    node.innerHTML = (isArrow || entity.type === 'actor' || isSeqType || entity.type === 'alt' || entity.type === 'loop') ? `
        <div class="node-body p-0 flex items-center justify-center w-full h-full">
            ${bodyContent}
        </div>
        ${resizeHandles}
        ${connHandles}
    ` : `
        <div class="node-header handle ${headerClass} px-3 py-2 text-[11px] font-bold border-b border-white/5 flex items-center justify-center gap-2">
            ${typeLabel ? `<span class="opacity-50 font-medium">${typeLabel}</span>` : ''}
            <span>${entity.name}</span>
        </div>
        <div class="node-body p-3">
            ${bodyContent}
        </div>
        ${resizeHandles}
        ${connHandles}
    `;

    // Interactivity
    node.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return; // Only left-click
        e.preventDefault(); // Prevents text selection on drag

        const hConnection = e.target.closest('.conn-handle');
        const hResize = e.target.closest('.node-resize-handle');
        const hLifeline = e.target.closest('.lifeline-hit-area');

        if (hConnection) {
            e.stopPropagation();
            startConnection(e, entity.id, hConnection.dataset.side);
        } else if (hLifeline) {
            e.stopPropagation();
            const rect = canvasContainer.getBoundingClientRect();
            const mouseY = (e.clientY - rect.top - panY) / currentZoom;
            const yOffset = mouseY - entity.y;
            startConnection(e, entity.id, 'lifeline', activeRelationshipType, yOffset);
        } else if (hResize) {
            e.stopPropagation();
            selectElement(entity.id, 'node');
            pushToHistory(); // Push before resize
            startNodeResize(e, entity, node, hResize.dataset.corner);
        } else {
            selectElement(entity.id, 'node');
            pushToHistory(); // Push before drag
            startNodeDrag(e, entity, node);
        }
        e.stopPropagation();
    });

    // Drop relationship on node
    node.addEventListener('dragover', (e) => e.preventDefault());
    node.addEventListener('drop', (e) => {
        const type = e.dataTransfer.getData('type');
        if (type && type.startsWith('rel-')) {
            e.preventDefault();
            e.stopPropagation();
            const relType = type.replace('rel-', '');
            // Start a connection from this node using the dropped type
            startConnection(e, entity.id, 'right', relType);
        }
    });

    return node;
}

// --- Drag & Drop ---
function startNodeDrag(e, entity, element) {
    const startX = e.clientX;
    const startY = e.clientY;
    const initialNodeX = entity.x;
    const initialNodeY = entity.y;

    // Find all relationships connected to this node
    const connectedRels = diagramModel.relationships.filter(r => r.from_id === entity.id || r.to_id === entity.id);

    const onMove = (moveEvent) => {
        const dx = (moveEvent.clientX - startX) / currentZoom;
        const dy = (moveEvent.clientY - startY) / currentZoom;

        entity.x = initialNodeX + dx;
        entity.y = initialNodeY + dy;

        element.style.left = `${entity.x}px`;
        element.style.top = `${entity.y}px`;

        // Update ONLY connected lines for zero lag
        connectedRels.forEach(rel => {
            const pathElGroup = relationshipElements.get(rel.id);
            if (pathElGroup) {
                const from = diagramModel.entities.find(en => en.id === rel.from_id);
                const to = diagramModel.entities.find(en => en.id === rel.to_id);
                if (from && to) {
                    updateBezierPath(pathElGroup, from, to, rel);
                }
            }
        });
    };

    const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
        saveModel();
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}

function startNodeResize(e, entity, element, corner) {
    const startX = e.clientX;
    const startY = e.clientY;
    const initialX = entity.x;
    const initialY = entity.y;
    const initialWidth = entity.width || 180;
    const initialHeight = entity.height || 120;

    const connectedRels = diagramModel.relationships.filter(r => r.from_id === entity.id || r.to_id === entity.id);

    const onMove = (moveEvent) => {
        const dx = (moveEvent.clientX - startX) / currentZoom;
        const dy = (moveEvent.clientY - startY) / currentZoom;

        let newX = initialX;
        let newY = initialY;
        let newW = initialWidth;
        let newH = initialHeight;

        const MIN_W = 50;
        const MIN_H = 50;

        if (corner === 'br' || corner === 'r' || corner === 'tr') {
            newW = Math.max(MIN_W, initialWidth + dx);
        }
        if (corner === 'br' || corner === 'b' || corner === 'bl') {
            newH = Math.max(MIN_H, initialHeight + dy);
        }

        if (corner === 'bl' || corner === 'l' || corner === 'tl') {
            const possibleW = initialWidth - dx;
            if (possibleW >= MIN_W) {
                newX = initialX + dx;
                newW = possibleW;
            } else {
                newX = initialX + (initialWidth - MIN_W);
                newW = MIN_W;
            }
        }

        if (corner === 'tr' || corner === 't' || corner === 'tl') {
            const possibleH = initialHeight - dy;
            if (possibleH >= MIN_H) {
                newY = initialY + dy;
                newH = possibleH;
            } else {
                newY = initialY + (initialHeight - MIN_H);
                newH = MIN_H;
            }
        }

        entity.x = newX;
        entity.y = newY;
        entity.width = newW;
        entity.height = newH;

        element.style.left = `${entity.x}px`;
        element.style.top = `${entity.y}px`;
        element.style.width = `${entity.width}px`;
        element.style.height = `${entity.height}px`;

        // Update connected lines
        connectedRels.forEach(rel => {
            const pathElGroup = relationshipElements.get(rel.id);
            if (pathElGroup) {
                const from = diagramModel.entities.find(en => en.id === rel.from_id);
                const to = diagramModel.entities.find(en => en.id === rel.to_id);
                if (from && to) {
                    updateBezierPath(pathElGroup, from, to, rel);
                }
            }
        });
        updatePropertyPanel();
    };

    const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
        saveModel();
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}

function updateBezierPath(pathElGroup, from, to, rel) {
    const { start: finalStart, end: finalEnd } = getEffectiveAnchors(from, to, rel);

    const startPos = getHandlePos(from.id, rel.fromYOffset !== undefined && rel.fromYOffset !== null ? 'lifeline' : finalStart, rel.fromYOffset);
    const endPos = getHandlePos(to.id, rel.toYOffset !== undefined && rel.toYOffset !== null ? 'lifeline' : finalEnd, rel.toYOffset);

    // Check if seq-to-seq connection
    const isSeqRel = seqTypes.includes(from.type) && seqTypes.includes(to.type);

    let sX = startPos.x;
    let sY = startPos.y;
    let eX = endPos.x;
    let eY = endPos.y;

    // Flexible sequence lines: no more forced horizontal eY = sY

    const d = isSeqRel
        ? `M ${sX} ${sY} L ${eX} ${eY} `
        : getBezierPathString(sX, sY, eX, eY, finalStart, finalEnd);

    // Update ALL paths in the group (visual path AND invisible hit path)
    if (pathElGroup.tagName.toLowerCase() === 'g') {
        const visualPath = pathElGroup.querySelector('path:not([stroke="transparent"])');
        if (visualPath) {
            visualPath.setAttribute("d", d);
            const isSelected = selectedElementId === rel.id;
            if (isSeqRel) {
                visualPath.setAttribute("stroke-width", isSelected ? "2.5" : "2");
            } else {
                const baseWidth = rel.strokeWidth || 2;
                visualPath.setAttribute("stroke-width", isSelected ? baseWidth + 1 : baseWidth);
            }
        }
        const hitPath = pathElGroup.querySelector('path[stroke="transparent"]');
        if (hitPath) hitPath.setAttribute("d", d);

        // Update drag handles if they exist
        const fromHandle = pathElGroup.querySelector('.rel-drag-handle[data-end="from"]');
        const toHandle = pathElGroup.querySelector('.rel-drag-handle[data-end="to"]');
        if (fromHandle) {
            fromHandle.setAttribute("cx", sX);
            fromHandle.setAttribute("cy", sY);
        }
        if (toHandle) {
            toHandle.setAttribute("cx", eX);
            toHandle.setAttribute("cy", eY);
        }
    } else {
        pathElGroup.setAttribute("d", d);
    }

    // Update label position if exists
    if (pathElGroup.tagName.toLowerCase() === 'g') {
        const textElements = pathElGroup.querySelectorAll('text');
        textElements.forEach(text => {
            // Find which label this is
            if (text.textContent === rel.label) {
                text.setAttribute("x", sX + (eX - sX) / 2);
                text.setAttribute("y", sY + (eY - sY) / 2 - 10);
            } else if (text.textContent === rel.fromLabel) {
                const pos = getMultiplicityPos(sX, sY, eX, eY, finalStart, true);
                text.setAttribute("x", pos.x);
                text.setAttribute("y", pos.y);
            } else if (text.textContent === rel.toLabel) {
                const pos = getMultiplicityPos(eX, eY, sX, sY, finalEnd, false);
                text.setAttribute("x", pos.x);
                text.setAttribute("y", pos.y);
            }
        });
    }
}

function getBestAnchors(from, to) {
    const fW = from.width || 180, fH = from.height || 120;
    const tW = to.width || 180, tH = to.height || 120;
    const fMidX = from.x + fW / 2, fMidY = from.y + fH / 2;
    const tMidX = to.x + tW / 2, tMidY = to.y + tH / 2;

    const dx = tMidX - fMidX;
    const dy = tMidY - fMidY;

    if (Math.abs(dx) > Math.abs(dy)) {
        return dx > 0 ? { start: 'right', end: 'left' } : { start: 'left', end: 'right' };
    } else {
        return dy > 0 ? { start: 'bottom', end: 'top' } : { start: 'top', end: 'bottom' };
    }
}

function getBezierPathString(sX, sY, eX, eY, sSide, eSide) {
    let cp1x = sX, cp1y = sY, cp2x = eX, cp2y = eY;
    const tension = 0.5;
    const dist = Math.sqrt((eX - sX) ** 2 + (eY - sY) ** 2) * tension;

    if (sSide === 'right') cp1x += dist;
    else if (sSide === 'left') cp1x -= dist;
    else if (sSide === 'top') cp1y -= dist;
    else if (sSide === 'bottom') cp1y += dist;

    if (eSide === 'right') cp2x += dist;
    else if (eSide === 'left') cp2x -= dist;
    else if (eSide === 'top') cp2y -= dist;
    else if (eSide === 'bottom') cp2y += dist;

    return `M ${sX} ${sY} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${eX} ${eY} `;
}

function getEffectiveAnchors(from, to, rel) {
    // For sequence types, always use horizontal anchors
    if (seqTypes.includes(from.type) && seqTypes.includes(to.type)) {
        const fromCenterX = from.x + (from.width || 100) / 2;
        const toCenterX = to.x + (to.width || 100) / 2;
        if (fromCenterX <= toCenterX) {
            return { start: 'right', end: 'left' };
        } else {
            return { start: 'left', end: 'right' };
        }
    }

    const best = getBestAnchors(from, to);
    return {
        start: rel.fromSide || best.start,
        end: rel.toSide || best.end
    };
}

// --- Connection Logic ---
let connectionStarted = false;
let connectionSourceId = null;
let connectionSide = null;
let tempLine = null;

function startConnection(e, sourceId, side, defaultType = activeRelationshipType, startYOffset = null) {
    connectionStarted = true;
    connectionSourceId = sourceId;
    connectionSide = side;

    // Create a temporary SVG line
    tempLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    tempLine.setAttribute("stroke", "#818cf8");
    tempLine.setAttribute("stroke-width", "2");
    tempLine.style.pointerEvents = "none";
    if (defaultType === 'dependency') {
        tempLine.setAttribute("stroke-dasharray", "5,5");
    } else {
        tempLine.setAttribute("stroke-dasharray", "4");
    }

    const svg = document.getElementById('connections-layer');
    svg.appendChild(tempLine);

    const onMove = (moveEvent) => {
        const rect = canvasContainer.getBoundingClientRect();
        const start = getHandlePos(sourceId, side, startYOffset);

        const endX = (moveEvent.clientX - rect.left - panX) / currentZoom;
        const endY = (moveEvent.clientY - rect.top - panY) / currentZoom;

        tempLine.setAttribute("x1", start.x);
        tempLine.setAttribute("y1", start.y);
        tempLine.setAttribute("x2", endX);
        tempLine.setAttribute("y2", endY);
    };

    const onEnd = (endEvent) => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onEnd);

        if (tempLine.parentNode) tempLine.parentNode.removeChild(tempLine);

        // Check if we dropped on another node
        const targetNode = endEvent.target.closest('.editor-node');
        if (targetNode && targetNode.dataset.id !== sourceId) {
            const targetId = targetNode.dataset.id;
            const targetEntity = diagramModel.entities.find(en => en.id === targetId);

            pushToHistory(); // Push before relationship creation

            // Calculate end Y offset if targeting a sequence node lifeline
            let toYOffset = null;
            const hLifeline = endEvent.target.closest('.lifeline-hit-area');
            if (hLifeline && targetEntity) {
                const rect = canvasContainer.getBoundingClientRect();
                const mouseY = (endEvent.clientY - rect.top - panY) / currentZoom;
                toYOffset = mouseY - targetEntity.y;
            }

            // Create new relationship
            let fromL = '', toL = '';

            const newRel = {
                id: crypto.randomUUID(),
                from_id: sourceId,
                to_id: targetId,
                type: defaultType,
                label: '',
                fromLabel: fromL,
                toLabel: toL,
                fromYOffset: startYOffset,
                toYOffset: toYOffset,
                strokeWidth: 2
            };

            diagramModel.relationships.push(newRel);
            saveModel();
            renderAll();
        }

        connectionStarted = false;
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onEnd);
}

function getHandlePos(nodeId, side, yOffset = null) {
    const entity = diagramModel.entities.find(e => e.id === nodeId);
    if (!entity) return { x: 0, y: 0 };

    const isSeq = seqTypes.includes(entity.type);

    // Type-aware defaults to match createNodeElement
    let w = entity.width;
    let h = entity.height;
    if (!w) {
        if (entity.type === 'actor') w = 60;
        else if (entity.type === 'alt' || entity.type === 'loop') w = 200;
        else if (entity.type === 'activation') w = 24;
        else if (isSeq) w = 100;
        else if (entity.type === 'usecase') w = 140;
        else w = 180;
    }
    if (!h) {
        if (entity.type === 'actor') h = 90;
        else if (entity.type === 'alt' || entity.type === 'loop') h = 150;
        else if (entity.type === 'activation') h = 200;
        else if (isSeq) h = 300;
        else if (entity.type === 'usecase') h = 70;
        else if (entity.type === 'bpmn-gateway') { w = 60; h = 60; }
        else if (entity.type === 'bpmn-start' || entity.type === 'bpmn-end') { w = 40; h = 40; }
        else if (entity.type === 'activity-decision') { w = 50; h = 50; }
        else if (entity.type === 'activity-initial') { w = 25; h = 25; }
        else if (entity.type === 'activity-final') { w = 30; h = 30; }
        else h = 120;
    }

    if (side === 'lifeline' || (isSeq && yOffset !== null)) {
        const centerX = entity.x + w / 2;
        return { x: centerX, y: entity.y + (yOffset !== null && yOffset !== undefined ? yOffset : h / 2) };
    }

    if (isSeq) {
        // For sequence types, left/right connect at the center (lifeline)
        const centerX = entity.x + w / 2;
        if (side === 'left' || side === 'right') return { x: centerX, y: entity.y + h / 2 };
        if (side === 'top') return { x: centerX, y: entity.y };
        if (side === 'bottom') return { x: centerX, y: entity.y + h };
        return { x: centerX, y: entity.y + h / 2 };
    }

    if (side === 'top') return { x: entity.x + w / 2, y: entity.y };
    if (side === 'bottom') return { x: entity.x + w / 2, y: entity.y + h };
    if (side === 'left') return { x: entity.x, y: entity.y + h / 2 };
    if (side === 'right') return { x: entity.x + w, y: entity.y + h / 2 };

    return { x: entity.x + w / 2, y: entity.y + h / 2 };
}

// --- Canvas Interactions ---
function initCanvasEvents() {
    canvasContainer.addEventListener('mousedown', (e) => {
        if (e.button === 0) { // Left click canvas to deselect
            selectElement(null);
        }
    });

    // Drag-over logic for sidebar drops
    canvasContainer.addEventListener('dragover', (e) => e.preventDefault());
    canvasContainer.addEventListener('drop', (e) => {
        e.preventDefault();
        const type = e.dataTransfer.getData('type');
        if (!type || type.startsWith('rel-')) return; // Fix: Don't create entities for relationship types dropped on canvas

        pushToHistory(); // Push before adding new node
        const rect = canvasContainer.getBoundingClientRect();

        // Calculate position considering zoom and pan
        const x = (e.clientX - rect.left - panX) / currentZoom;
        const y = (e.clientY - rect.top - panY) / currentZoom;

        let w = 180, h = 120;
        if (type === 'actor') { w = 60; h = 90; }
        else if (type === 'alt' || type === 'loop') { w = 200; h = 150; }
        else if (type === 'activation') { w = 24; h = 200; }
        else if (seqDropTypes.includes(type)) { w = 100; h = 300; }
        else if (type === 'usecase') { w = 140; h = 70; }
        else if (type === 'bpmn-task') { w = 160; h = 100; }
        else if (type === 'bpmn-gateway') { w = 60; h = 60; }
        else if (type === 'bpmn-start' || type === 'bpmn-end') { w = 40; h = 40; }
        else if (type === 'activity-action') { w = 140; h = 60; }
        else if (type === 'activity-decision') { w = 50; h = 50; }
        else if (type === 'activity-initial') { w = 25; h = 25; }
        else if (type === 'activity-final') { w = 30; h = 30; }

        const newEntity = {
            id: crypto.randomUUID(),
            name: `New${type.charAt(0).toUpperCase() + type.slice(1)} `,
            type: type,
            attributes: [],
            methods: [],
            x: x - (w / 2),
            y: y - (h / 2),
            width: w,
            height: h
        };

        diagramModel.entities.push(newEntity);
        saveModel();
        renderAll();
        selectElement(newEntity.id, 'node');
    });
}

// --- Zoom & Pan ---
function initZoomControls() {
    const applyZoom = () => {
        canvasContent.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
        zoomLevelText.textContent = `${Math.round(currentZoom * 100)}% `;
    };

    document.getElementById('zoomIn').onclick = () => { currentZoom *= 1.1; applyZoom(); };
    document.getElementById('zoomOut').onclick = () => { currentZoom /= 1.1; applyZoom(); };

    canvasContainer.addEventListener('wheel', (e) => {
        if (e.ctrlKey) {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            currentZoom *= delta;
            applyZoom();
        }
    }, { passive: false });
}

function initPanControls() {
    canvasContainer.addEventListener('mousedown', (e) => {
        if (e.button === 1 || (e.button === 0 && e.altKey)) { // Middle click or Alt+Left
            isPanning = true;
            dragStartX = e.clientX - panX;
            dragStartY = e.clientY - panY;
            canvasContainer.style.cursor = 'grabbing';
            e.preventDefault();
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        panX = e.clientX - dragStartX;
        panY = e.clientY - dragStartY;
        canvasContent.style.transform = `translate(${panX}px, ${panY}px) scale(${currentZoom})`;
    });

    window.addEventListener('mouseup', () => {
        isPanning = false;
        canvasContainer.style.cursor = 'crosshair';
    });
}

// --- Sidebar ---
function initAccordion() {
    document.querySelectorAll('.accordion-header').forEach(header => {
        header.onclick = () => {
            const content = header.nextElementSibling;
            content.classList.toggle('hidden');
        };
    });

    document.querySelectorAll('.draggable-shape').forEach(shape => {
        shape.setAttribute('draggable', true);
        shape.ondragstart = (e) => {
            e.dataTransfer.setData('type', shape.dataset.type);
        };
    });

    // Connector Tool selection
    document.querySelectorAll('.connector-tool').forEach(btn => {
        btn.onclick = () => {
            document.querySelectorAll('.connector-tool').forEach(b => b.classList.remove('active', 'bg-indigo-600/40'));
            btn.classList.add('active', 'bg-indigo-600/40');
            activeRelationshipType = btn.dataset.rel;
        };
    });
}

let activeRelationshipType = 'association';

// --- Connections ---
function renderConnections() {
    relationshipElements.clear();
    const svg = document.getElementById('connections-layer');
    if (!svg) return;

    // Keep defs
    const defs = svg.querySelector('defs');
    // Clear everything EXCEPT defs
    Array.from(svg.childNodes).forEach(child => {
        if (child !== defs) svg.removeChild(child);
    });

    diagramModel.relationships.forEach(rel => {
        const from = diagramModel.entities.find(e => e.id === rel.from_id);
        const to = diagramModel.entities.find(e => e.id === rel.to_id);
        if (from && to) {
            const pathEl = drawBezierConnection(from, to, rel);
            svg.appendChild(pathEl);
            relationshipElements.set(rel.id, pathEl);
        }
    });
}

function drawBezierConnection(from, to, rel) {
    const { start, end } = getEffectiveAnchors(from, to, rel);
    const startPos = getHandlePos(from.id, rel.fromYOffset !== undefined && rel.fromYOffset !== null ? 'lifeline' : start, rel.fromYOffset);
    const endPos = getHandlePos(to.id, rel.toYOffset !== undefined && rel.toYOffset !== null ? 'lifeline' : end, rel.toYOffset);

    // Check if this is a seq-to-seq connection
    const isSeqRel = seqTypes.includes(from.type) && seqTypes.includes(to.type);

    let sX = startPos.x;
    let sY = startPos.y;
    let eX = endPos.x;
    let eY = endPos.y;

    // Remove forced horizontal constraint for flexible sequence diagrams
    // if (isSeqRel) { eY = sY; ... } 

    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    let d;
    if (rel.from_id === rel.to_id) {
        // Self-message (Recursive)
        const offset = 40;
        const vGap = Math.abs(eY - sY) < 10 ? 30 : 0; // Add vertical gap if points are too close
        d = `M ${sX} ${sY} L ${sX + offset} ${sY} L ${sX + offset} ${eY + vGap} L ${eX} ${eY + vGap} `;
    } else if (isSeqRel) {
        // Straight horizontal line for sequence diagrams
        d = `M ${sX} ${sY} L ${eX} ${eY} `;
    } else {
        d = getBezierPathString(sX, sY, eX, eY, start, end);
    }

    const isSelected = selectedElementId === rel.id;

    if (isSeqRel) {
        // Sequence diagram style: clean visible line
        path.setAttribute("d", d);
        path.setAttribute("stroke", isSelected ? "#818cf8" : "#4f46e5");
        path.setAttribute("stroke-width", isSelected ? "2.5" : "2");
        path.setAttribute("fill", "none");
        // Use seq-specific arrow marker (no gap)
        const suffix = isSelected ? "-selected" : "";
        path.setAttribute("marker-end", `url(#arrow-seq${suffix})`);
    } else {
        const baseWidth = rel.strokeWidth || 2;
        path.setAttribute("d", d);
        path.setAttribute("stroke", isSelected ? "#818cf8" : "#4f46e5");
        path.setAttribute("stroke-width", isSelected ? baseWidth + 1 : baseWidth);
        path.setAttribute("fill", "none");

        // Marker mapping
        const suffix = isSelected ? "-selected" : "";
        let marker = `url(#arrow-assoc${suffix})`;
        if (rel.type === 'inheritance') marker = `url(#arrow-inherit${suffix})`;
        if (rel.type === 'aggregation') marker = `url(#arrow-aggregation${suffix})`;
        if (rel.type === 'composition') marker = `url(#arrow-composition${suffix})`;
        if (rel.type === 'dependency') {
            marker = `url(#arrow-dependency${suffix})`;
            path.setAttribute("stroke-dasharray", "5,5");
        } else if (rel.type === 'association') {
            marker = `url(#arrow-assoc${suffix})`;
        }
        path.setAttribute("marker-end", marker);
    }

    // Thick invisible path for easier clicking
    const hitPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    hitPath.setAttribute("d", d);
    hitPath.setAttribute("stroke", "transparent");
    hitPath.setAttribute("stroke-width", "20");
    hitPath.setAttribute("fill", "none");
    hitPath.style.cursor = 'pointer';
    hitPath.style.pointerEvents = 'stroke';

    const onRelClick = (e) => {
        e.preventDefault(); // Prevents text selection
        selectElement(rel.id, 'rel');

        // Direct Drag: If user holds and moves, start dragging the nearest endpoint
        const startX = e.clientX;
        const startY = e.clientY;
        const rect = canvasContainer.getBoundingClientRect();
        const mouseX = (e.clientX - rect.left - panX) / currentZoom;
        const mouseY = (e.clientY - rect.top - panY) / currentZoom;

        const sPos = getHandlePos(rel.from_id, rel.fromSide || getEffectiveAnchors(from, to, rel).start);
        const ePos = getHandlePos(rel.to_id, rel.toSide || getEffectiveAnchors(from, to, rel).end);

        const distStart = Math.sqrt((mouseX - sPos.x) ** 2 + (mouseY - sPos.y) ** 2);
        const distEnd = Math.sqrt((mouseX - ePos.x) ** 2 + (mouseY - ePos.y) ** 2);
        const endType = distStart < distEnd ? 'from' : 'to';

        const onMouseMoveOnce = (mE) => {
            if (Math.abs(mE.clientX - startX) > 5 || Math.abs(mE.clientY - startY) > 5) {
                window.removeEventListener('mousemove', onMouseMoveOnce);
                pushToHistory(); // Push before rel drag
                startRelDrag(mE, rel, endType);
            }
        };
        window.addEventListener('mousemove', onMouseMoveOnce);
        window.addEventListener('mouseup', () => window.removeEventListener('mousemove', onMouseMoveOnce), { once: true });

        e.stopPropagation();
    };

    path.onmousedown = onRelClick;
    hitPath.onmousedown = onRelClick;

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.appendChild(path);
    g.appendChild(hitPath);

    // Add drag handles if selected
    if (isSelected) {
        const fromHandle = createRelDragHandle(sX, sY, rel, 'from');
        const toHandle = createRelDragHandle(eX, eY, rel, 'to');
        g.appendChild(fromHandle);
        g.appendChild(toHandle);
    }

    // Label Rendering
    if (rel.label) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        const midX = sX + (eX - sX) / 2;
        const midY = sY + (eY - sY) / 2;
        const fontSize = rel.labelFontSize || (isSeqRel ? 13 : 10);
        text.setAttribute("x", midX);
        if (isSeqRel) {
            // Position label just above the line (4px gap)
            text.setAttribute("y", midY - 4);
        } else {
            text.setAttribute("y", midY - 10);
        }
        text.setAttribute("fill", isSeqRel ? "#e2e8f0" : "#94a3b8");
        text.setAttribute("font-size", fontSize);
        text.setAttribute("font-weight", "bold");
        text.setAttribute("text-anchor", "middle");
        text.textContent = rel.label;
        text.style.pointerEvents = 'none';
        g.appendChild(text);
    }

    // Side-specific Multiplicity Labels
    if (rel.fromLabel) {
        const pos = getMultiplicityPos(sX, sY, eX, eY, start, true);
        g.appendChild(createMultiplicityText(pos.x, pos.y, rel.fromLabel));
    }
    if (rel.toLabel) {
        const pos = getMultiplicityPos(eX, eY, sX, sY, end, false);
        g.appendChild(createMultiplicityText(pos.x, pos.y, rel.toLabel));
    }

    return g;
}

function createRelDragHandle(x, y, rel, endType) {
    const handle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    handle.setAttribute("cx", x);
    handle.setAttribute("cy", y);
    handle.setAttribute("r", "6");
    handle.setAttribute("fill", "#818cf8");
    handle.setAttribute("stroke", "white");
    handle.setAttribute("stroke-width", "2");
    handle.setAttribute("class", "rel-drag-handle");
    handle.dataset.end = endType;
    handle.style.cursor = 'move';
    handle.style.pointerEvents = 'all';

    handle.onmousedown = (e) => {
        startRelDrag(e, rel, endType);
        e.stopPropagation();
    };
    return handle;
}

function startRelDrag(e, rel, endType) {
    const startX = e.clientX;
    const startY = e.clientY;

    const onMove = (moveEvent) => {
        const rect = canvasContainer.getBoundingClientRect();
        const mouseX = (moveEvent.clientX - rect.left - panX) / currentZoom;
        const mouseY = (moveEvent.clientY - rect.top - panY) / currentZoom;

        // Visual feedback
        const pathGroup = relationshipElements.get(rel.id);
        if (pathGroup) {
            // Disable pointer events on handle during drag to allow snapping to handles underneath
            const handle = pathGroup.querySelector(`.rel-drag-handle[data-end="${endType}"]`);
            if (handle) {
                handle.style.pointerEvents = 'none';
                handle.setAttribute("cx", mouseX);
                handle.setAttribute("cy", mouseY);
            }

            const from = diagramModel.entities.find(en => en.id === rel.from_id);
            const to = diagramModel.entities.find(en => en.id === rel.to_id);

            let sX, sY, eX, eY;
            const fromPos = getHandlePos(rel.from_id, rel.fromSide || getEffectiveAnchors(from, to, rel).start, rel.fromYOffset);
            const toPos = getHandlePos(rel.to_id, rel.toSide || getEffectiveAnchors(from, to, rel).end, rel.toYOffset);

            if (endType === 'from') {
                sX = mouseX; sY = mouseY;
                eX = toPos.x; eY = toPos.y;
            } else {
                sX = fromPos.x; sY = fromPos.y;
                eX = mouseX; eY = mouseY;
            }

            const isSeqRel = seqTypes.includes(from.type) && seqTypes.includes(to.type);

            const d = isSeqRel
                ? `M ${sX} ${sY} L ${eX} ${eY} `
                : getBezierPathString(sX, sY, eX, eY, rel.fromSide || 'right', rel.toSide || 'left');

            const visualPath = pathGroup.querySelector('path:not([stroke="transparent"])');
            if (visualPath) visualPath.setAttribute("d", d);
            const hitPath = pathGroup.querySelector('path[stroke="transparent"]');
            if (hitPath) hitPath.setAttribute("d", d);
        }
    };

    const onUp = (upEvent) => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);

        // Re-enable pointer events on handle
        const pathGroup = relationshipElements.get(rel.id);
        if (pathGroup) {
            const handle = pathGroup.querySelector(`.rel-drag-handle[data-end="${endType}"]`);
            if (handle) handle.style.pointerEvents = 'all';
        }

        const target = upEvent.target.closest('.conn-handle');
        const hLifeline = upEvent.target.closest('.lifeline-hit-area');

        if (target || hLifeline) {
            pushToHistory();
            const nodeId = (target || hLifeline).closest('.editor-node').dataset.id;
            const side = target ? target.dataset.side : 'lifeline';

            let yOffset = null;
            if (hLifeline) {
                const rect = canvasContainer.getBoundingClientRect();
                const mouseY = (upEvent.clientY - rect.top - panY) / currentZoom;
                const entity = diagramModel.entities.find(e => e.id === nodeId);
                if (entity) yOffset = mouseY - entity.y;
            }

            if (endType === 'from') {
                rel.from_id = nodeId;
                rel.fromSide = target ? side : null;
                rel.fromYOffset = yOffset;
            } else {
                rel.to_id = nodeId;
                rel.toSide = target ? side : null;
                rel.toYOffset = yOffset;
            }
            saveModel();
            renderAll();
        } else {
            // Revert or stay
            renderAll();
        }
    };

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}
function getMultiplicityPos(x, y, otherX, otherY, side, isStart) {
    const offset = 25; // Distance from node
    const sideOffset = 15; // Lateral offset from line
    let mX = x, mY = y;

    if (side === 'right') { mX += offset; mY -= sideOffset; }
    else if (side === 'left') { mX -= offset; mY -= sideOffset; }
    else if (side === 'top') { mY -= offset; mX += sideOffset; }
    else if (side === 'bottom') { mY += offset; mX += sideOffset; }

    return { x: mX, y: mY };
}

function createMultiplicityText(x, y, label) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", x);
    text.setAttribute("y", y);
    text.setAttribute("fill", "#6366f1");
    text.setAttribute("font-size", "12");
    text.setAttribute("font-weight", "800");
    text.setAttribute("text-anchor", "middle");
    text.textContent = label;
    text.style.pointerEvents = 'none';
    return text;
}

// --- Property Panel ---
function selectElement(id, type) {
    if (selectedElementId === id) return;

    selectedElementId = id;

    // Update visual selection for nodes
    document.querySelectorAll('.editor-node').forEach(node => {
        if (node.dataset.id === id) {
            node.classList.add('selected');
        } else {
            node.classList.remove('selected');
        }
    });

    // Update visual selection for relationships (SVG paths)
    relationshipElements.forEach((pathGroup, relId) => {
        const path = pathGroup.querySelector('path');
        if (path) {
            const isSelected = (relId === id);
            const rel = diagramModel.relationships.find(r => r.id === relId);
            const baseWidth = rel?.strokeWidth || 2;

            path.setAttribute("stroke", isSelected ? "#818cf8" : "#4f46e5");
            path.setAttribute("stroke-width", isSelected ? baseWidth + 1 : baseWidth);

            // Update marker
            const suffix = isSelected ? "-selected" : "";
            let marker = `url(#arrow-assoc${suffix})`;
            if (rel) {
                if (rel.type === 'inheritance') marker = `url(#arrow-inherit${suffix})`;
                if (rel.type === 'aggregation') marker = `url(#arrow-aggregation${suffix})`;
                if (rel.type === 'composition') marker = `url(#arrow-composition${suffix})`;
                if (rel.type === 'dependency') marker = `url(#arrow-dependency${suffix})`;
                else if (rel.type === 'association') marker = `url(#arrow-assoc${suffix})`;
                path.setAttribute("marker-end", marker);
            }

            // Surgically add/remove handles
            const existingHandles = pathGroup.querySelectorAll('.rel-drag-handle');
            if (isSelected && existingHandles.length === 0 && rel) {
                const from = diagramModel.entities.find(e => e.id === rel.from_id);
                const to = diagramModel.entities.find(e => e.id === rel.to_id);
                const { start, end } = getEffectiveAnchors(from, to, rel);

                const sPos = getHandlePos(from.id, rel.fromYOffset !== undefined && rel.fromYOffset !== null ? 'lifeline' : start, rel.fromYOffset);
                const ePos = getHandlePos(to.id, rel.toYOffset !== undefined && rel.toYOffset !== null ? 'lifeline' : end, rel.toYOffset);

                const sX = sPos.x;
                const sY = sPos.y;
                const eX = ePos.x;
                const eY = ePos.y;

                pathGroup.appendChild(createRelDragHandle(sX, sY, rel, 'from'));
                pathGroup.appendChild(createRelDragHandle(eX, eY, rel, 'to'));
            } else if (!isSelected && existingHandles.length > 0) {
                existingHandles.forEach(h => h.remove());
            }
        }
    });

    updatePropertyPanel();
}

function updatePropertyPanel() {
    const noSel = document.getElementById('no-selection');
    const entityForm = document.getElementById('entity-prop-form');
    const relForm = document.getElementById('rel-prop-form');

    noSel.classList.remove('hidden');
    entityForm.classList.add('hidden');
    relForm.classList.add('hidden');

    if (!selectedElementId) return;

    const entity = diagramModel.entities.find(e => e.id === selectedElementId);
    if (entity) {
        noSel.classList.add('hidden');
        entityForm.classList.remove('hidden');

        document.getElementById('nodeName').value = entity.name;
        document.getElementById('nodeType').value = entity.type;
        document.getElementById('nodeWidth').value = Math.round(entity.width || 180);
        document.getElementById('nodeHeight').value = Math.round(entity.height || 120);
        document.getElementById('nodeAttributes').value = entity.attributes.join('\n');
        document.getElementById('nodeMethods').value = entity.methods.join('\n');
    } else {
        const rel = diagramModel.relationships.find(r => r.id === selectedElementId);
        if (rel) {
            noSel.classList.add('hidden');
            relForm.classList.remove('hidden');
            document.getElementById('relLabel').value = rel.label || '';
            document.getElementById('relFromLabel').value = rel.fromLabel || '';
            document.getElementById('relToLabel').value = rel.toLabel || '';
            document.getElementById('relType').value = rel.type;
            document.getElementById('relThickness').value = rel.strokeWidth || 2;

            // Check if this is a seq-to-seq connection
            const fromE = diagramModel.entities.find(e => e.id === rel.from_id);
            const toE = diagramModel.entities.find(e => e.id === rel.to_id);
            const isSeqRel = fromE && toE && seqTypes.includes(fromE.type) && seqTypes.includes(toE.type);

            // Show/hide fields based on connection type
            const relLabelGroup = document.getElementById('relLabel').closest('div');
            const relFromLabelGroup = document.getElementById('relFromLabel').closest('.grid');
            const relTypeGroup = document.getElementById('relType').closest('div');
            const relThicknessGroup = document.getElementById('relThickness').closest('div');

            // For seq connections: show label (message) + font size, hide everything else
            // For class connections: hide label (it's in context menu), show everything
            if (relLabelGroup) {
                relLabelGroup.classList.toggle('hidden', !isSeqRel);
                if (isSeqRel) {
                    const currentFontSize = rel.labelFontSize || 13;
                    relLabelGroup.innerHTML = `
                        <label class="block text-[10px] font-bold text-dim mb-2 uppercase tracking-tighter">Message Label</label>
                        <input type="text" id="relLabel" value="${rel.label || ''}" placeholder="e.g. login(user, pass)"
                            class="w-full bg-black/50 border border-white/10 rounded-lg p-2.5 text-sm focus:border-indigo-500 outline-none transition-all mb-4">
                    <label class="block text-[10px] font-bold text-dim mb-2 uppercase tracking-tighter">Label Size (${currentFontSize}px)</label>
                    <input type="range" id="relLabelFontSize" min="8" max="24" step="1" value="${currentFontSize}"
                        class="w-full h-1.5 bg-black/50 rounded-lg appearance-none cursor-pointer accent-indigo-500">
                        <div class="flex justify-between text-[8px] text-dim mt-1">
                            <span>8px</span>
                            <span>24px</span>
                        </div>
                        `;
                    document.getElementById('relLabel').oninput = (e) => { changeSelectedRel('label', e.target.value); };
                    document.getElementById('relLabelFontSize').oninput = (e) => {
                        changeSelectedRel('labelFontSize', parseInt(e.target.value));
                        e.target.previousElementSibling.previousElementSibling.textContent = `Label Size (${e.target.value}px)`;
                    };
                }
            }
            if (relFromLabelGroup) relFromLabelGroup.style.display = isSeqRel ? 'none' : '';
            if (relTypeGroup) relTypeGroup.style.display = isSeqRel ? 'none' : '';
            if (relThicknessGroup) relThicknessGroup.style.display = isSeqRel ? 'none' : '';

            // Update Anchor selection buttons
            const anchorGroup = document.getElementById('anchor-selection-group');
            if (anchorGroup) {
                anchorGroup.style.display = isSeqRel ? 'none' : '';
                if (!isSeqRel) {
                    // Sync From Anchor buttons
                    const fromAnchor = rel.fromSide || 'auto';
                    anchorGroup.querySelectorAll('[onclick*="\'from\'"]').forEach(btn => {
                        const side = btn.dataset.side;
                        btn.classList.toggle('active', side === fromAnchor);
                    });
                    // Sync To Anchor buttons
                    const toAnchor = rel.toSide || 'auto';
                    anchorGroup.querySelectorAll('[onclick*="\'to\'"]').forEach(btn => {
                        const side = btn.dataset.side;
                        btn.classList.toggle('active', side === toAnchor);
                    });
                }
            }
        }
    }
}

// --- Form Listeners ---
document.getElementById('nodeName').oninput = (e) => { changeSelected('name', e.target.value); };
document.getElementById('nodeType').onchange = (e) => { changeSelected('type', e.target.value); };
document.getElementById('nodeWidth').oninput = (e) => { changeSelected('width', parseInt(e.target.value) || 0); };
document.getElementById('nodeHeight').oninput = (e) => { changeSelected('height', parseInt(e.target.value) || 0); };
document.getElementById('nodeAttributes').oninput = (e) => { changeSelected('attributes', e.target.value.split('\n')); };
document.getElementById('nodeMethods').oninput = (e) => { changeSelected('methods', e.target.value.split('\n')); };

document.getElementById('relLabel').oninput = (e) => { changeSelectedRel('label', e.target.value); };
document.getElementById('relFromLabel').oninput = (e) => { changeSelectedRel('fromLabel', e.target.value); };
document.getElementById('relToLabel').oninput = (e) => { changeSelectedRel('toLabel', e.target.value); };
document.getElementById('relType').onchange = (e) => { changeSelectedRel('type', e.target.value); };
document.getElementById('relThickness').oninput = (e) => { changeSelectedRel('strokeWidth', parseInt(e.target.value)); };

function deleteSelected() {
    if (!selectedElementId) return;
    const nodeIdx = diagramModel.entities.findIndex(en => en.id === selectedElementId);
    if (nodeIdx !== -1) {
        diagramModel.entities.splice(nodeIdx, 1);
        diagramModel.relationships = diagramModel.relationships.filter(r => r.from_id !== selectedElementId && r.to_id !== selectedElementId);
    } else {
        diagramModel.relationships = diagramModel.relationships.filter(r => r.id !== selectedElementId);
    }
    selectedElementId = null;
    saveModel();
    renderAll();

}

// Map all delete buttons
['deleteNode', 'deleteNodeProp'].forEach(id => {
    const btn = document.getElementById(id);
    if (btn) btn.onclick = deleteSelected;
});

function changeSelected(key, val) {
    const entity = diagramModel.entities.find(e => e.id === selectedElementId);
    if (entity) {
        if (entity[key] === val) return; // No change
        pushToHistory();
        entity[key] = val;
        saveModel();

        // Partial update if possible
        if (key === 'name' || key === 'type' || key === 'attributes' || key === 'methods' || key === 'width' || key === 'height') {
            const nodeEl = nodeElements.get(selectedElementId);
            if (nodeEl) {
                const newNodeEl = createNodeElement(entity);
                nodeEl.replaceWith(newNodeEl);
                nodeElements.set(entity.id, newNodeEl);

                // Re-render connections if height/width might have changed
                renderConnections();
            }
        } else {
            renderAll();
        }
    }
}

function changeSelectedRel(key, val) {
    const rel = diagramModel.relationships.find(r => r.id === selectedElementId);
    if (rel) {
        if (rel[key] === val) return; // No change
        pushToHistory();
        rel[key] = val;
        saveModel();

        // Surgical update
        const pathGroup = relationshipElements.get(rel.id);
        if (pathGroup) {
            const from = diagramModel.entities.find(e => e.id === rel.from_id);
            const to = diagramModel.entities.find(e => e.id === rel.to_id);
            if (from && to) {
                // For changes that affect markers or structure, we recreate the group
                if (key === 'type' || key === 'label' || key === 'fromLabel' || key === 'toLabel' || key === 'fromSide' || key === 'toSide') {
                    const newPathGroup = drawBezierConnection(from, to, rel);
                    pathGroup.replaceWith(newPathGroup);
                    relationshipElements.set(rel.id, newPathGroup);
                } else {
                    // For changes like strokeWidth or positions (during drag), we just update
                    updateBezierPath(pathGroup, from, to, rel);
                }
            }
        } else {
            renderAll();
        }
    }
}

function setRelAnchor(endType, side) {
    if (!selectedElementId) return;
    const rel = diagramModel.relationships.find(r => r.id === selectedElementId);
    if (rel) {
        const key = endType === 'from' ? 'fromSide' : 'toSide';
        if (rel[key] === side) return;
        pushToHistory();
        rel[key] = side;
        saveModel();
        renderAll();
        updatePropertyPanel();
    }
}

// Delete Logic
const deleteNode = () => {
    diagramModel.entities = diagramModel.entities.filter(e => e.id !== selectedElementId);
    diagramModel.relationships = diagramModel.relationships.filter(r => r.from_id !== selectedElementId && r.to_id !== selectedElementId);
    selectedElementId = null;
    saveModel();
    renderAll();
};

document.getElementById('deleteNode').onclick = deleteNode;
const deleteNodeProp = document.getElementById('deleteNodeProp');
if (deleteNodeProp) deleteNodeProp.onclick = deleteNode;



document.getElementById('deleteRel').onclick = () => {
    diagramModel.relationships = diagramModel.relationships.filter(r => r.id !== selectedElementId);
    selectedElementId = null;
    saveModel();
    renderAll();
};

// --- Integration ---

// Save to Main: render the model and push the result to the main page via localStorage
document.getElementById('saveToMainBtn').onclick = async () => {
    const btn = document.getElementById('saveToMainBtn');
    const originalHTML = btn.innerHTML;
    btn.innerHTML = `<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Saving...`;
    btn.disabled = true;

    try {
        // 1. Save model to localStorage
        saveModel();

        // 2. Call the backend to render the model into PlantUML + PNG
        const response = await fetch('http://127.0.0.1:8002/render-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: diagramModel })
        });

        if (!response.ok) throw new Error('Render failed');

        const result = await response.json();

        // 3. Store the rendered diagram in localStorage so the main page can pick it up
        const renderedData = {
            diagram_png_base64: result.diagram_png_base64 || null,
            diagram_source: result.diagram_source || null,
            timestamp: Date.now()
        };
        localStorage.setItem('nexus_rendered_diagram', JSON.stringify(renderedData));

        // 4. Show the success modal
        document.getElementById('exportModal').classList.remove('hidden');
        document.getElementById('exportModal').classList.add('flex');

    } catch (e) {
        console.error('Save to main failed:', e);
        alert('Failed to save and render diagram. Make sure the backend is running on http://127.0.0.1:8002');
    } finally {
        btn.innerHTML = originalHTML;
        btn.disabled = false;
    }
};

document.getElementById('exportBtn').onclick = () => {
    saveModel();
    document.getElementById('exportModal').classList.remove('hidden');
    document.getElementById('exportModal').classList.add('flex');
};

document.getElementById('stayBtn').onclick = () => {
    document.getElementById('exportModal').classList.add('hidden');
};

document.getElementById('closeEditorBtn').onclick = () => {
    window.close();
};

document.getElementById('renderBtn').onclick = async () => {
    const btn = document.getElementById('renderBtn');
    btn.textContent = 'Generating...';
    try {
        const response = await fetch('http://127.0.0.1:8002/render-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: diagramModel })
        });
        const result = await response.json();
        if (result.diagram_png_base64) {
            // Download PNG
            const link = document.createElement('a');
            link.href = `data:image/png;base64,${result.diagram_png_base64}`;
            link.download = 'diagram.png';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    } catch (e) {
        alert('Failed to render.');
    } finally {
        btn.textContent = 'Download PNG';
    }
};


