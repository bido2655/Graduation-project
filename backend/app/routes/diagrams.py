"""
Diagram Routes - Endpoints for diagram generation.
"""
import asyncio
import re
import traceback
from fastapi import APIRouter, HTTPException

from ..models import (
    DiagramRequest,
    DiagramResponse,
    RenderRequest,
    GenerateModelRequest,
    RenderModelRequest,
    ParsePlantUMLRequest,
)
# Import DiagramModel components directly to avoid circular imports if any, or just for clarity
from ..models.diagram_model import DiagramModel, DiagramEntity, DiagramRelationship
from ..generators import generate_plantuml_code, generate_code, generate_plantuml_from_model
from ..services import encode_plantuml, render_plantuml_to_png

router = APIRouter()


def _parse_plantuml_to_model(plantuml_code: str) -> DiagramModel:
    """
    Very small, best-effort PlantUML parser that understands:
      - class "Name" as "ID" { ... }
      - class Name { ... }
      - entity "Name" as ID { ... }
      - relationships like: "ID1" --> "ID2" : Optional label
      - ERD crow's foot notation: ID1 ||..|{ ID2 : label

    It is intentionally conservative and focused on the format we generate
    in `generate_plantuml_from_model`. It will not support every possible
    PlantUML construct but is enough to keep entities + relations in sync
    with the visual editor.
    """
    entities_by_id: dict[str, DiagramEntity] = {}
    relationships: list[DiagramRelationship] = []

    lines = plantuml_code.splitlines()

    current_entity_id: str | None = None
    current_entity_attrs: list[str] = []
    current_entity_methods: list[str] = []

    # Regexes for entities and relationships
    class_with_alias_re = re.compile(r'^\s*class\s+"([^"]+)"\s+as\s+"?([^"\s{]+)"?\s*\{?')
    class_simple_re = re.compile(r'^\s*class\s+([A-Za-z0-9_]+)')
    # ERD entity syntax: entity "EntityName" as e01 { or entity EntityName as e01 {
    entity_with_alias_re = re.compile(r'^\s*entity\s+"?([^"\s]+)"?\s+as\s+([A-Za-z0-9_]+)')
    # Class diagram relationships with optional multiplicities
    # Captures: from_id, from_mult, arrow, to_mult, to_id, label
    # Supports: e_uuid1 "1" --> "*" e_uuid2 : label, A --> B, etc.
    rel_re = re.compile(
        r'^\s*"?([^"\s]+)"?\s*(?:"([^"]*)")?\s*([<>|.*o\-]+)\s*(?:"([^"]*)")?\s*"?([^"\s:]+)"?(?:\s*:\s*(.+))?\s*$'
    )
    # ERD crow's foot relationships: e01 ||..|{ e02 : label or "Entity1" ||..|{ "Entity2"
    erd_rel_re = re.compile(
        r'^\s*"?([A-Za-z0-9_]+)"?\s+([\|\}][|\}]?\.\.[|\{][|\{]?)\s+"?([A-Za-z0-9_]+)"?(?:\s*:\s*(.+))?\s*$'
    )

    def flush_current_entity() -> None:
        nonlocal current_entity_id, current_entity_attrs, current_entity_methods
        if current_entity_id is None:
            return
        entity = entities_by_id.get(current_entity_id)
        if entity:
            entity.attributes = [a for a in current_entity_attrs if a.strip()]
            entity.methods = [m for m in current_entity_methods if m.strip()]
        current_entity_id = None
        current_entity_attrs = []
        current_entity_methods = []

    for raw_line in lines:
        line = raw_line.strip()

        # End of class block
        if line.startswith("}") and current_entity_id is not None:
            flush_current_entity()
            continue

        # Start of class
        m_alias = class_with_alias_re.match(line)
        if m_alias:
            flush_current_entity()
            name, eid = m_alias.groups()
            entities_by_id.setdefault(
                eid,
                DiagramEntity(
                    id=eid,
                    name=name,
                    type="class",
                    attributes=[],
                    methods=[],
                ),
            )
            current_entity_id = eid
            continue

        m_simple = class_simple_re.match(line)
        if m_simple and " as " not in line:
            flush_current_entity()
            name = m_simple.group(1)
            eid = name
            entities_by_id.setdefault(
                eid,
                DiagramEntity(
                    id=eid,
                    name=name,
                    type="class",
                    attributes=[],
                    methods=[],
                ),
            )
            current_entity_id = eid
            continue

        # ERD entity syntax
        m_entity = entity_with_alias_re.match(line)
        if m_entity:
            flush_current_entity()
            name, eid = m_entity.groups()
            entities_by_id.setdefault(
                eid,
                DiagramEntity(
                    id=eid,
                    name=name,
                    type="table",  # ERD entities are tables
                    attributes=[],
                    methods=[],
                ),
            )
            current_entity_id = eid
            continue

        # Inside a class block: treat lines as attributes/methods
        if current_entity_id is not None and line and not line.startswith("@"):
            # Simple heuristic: lines with '(' are methods, otherwise attributes
            if "(" in line and ")" in line:
                current_entity_methods.append(line)
            else:
                current_entity_attrs.append(line)
            continue

        # Relationships
        m_rel = rel_re.match(line)
        if m_rel:
            from_id, from_mult, arrow, to_mult, to_id, label = m_rel.groups()

            # Map arrow to relationship type
            rel_type = "association"
            # Handle both arrow directions: --|> and <|--
            if "--|>" in arrow or "<|--" in arrow or "<|" in arrow or "|>" in arrow:
                rel_type = "inheritance"
            elif "*--" in arrow or "--*" in arrow:
                rel_type = "composition"
            elif "o--" in arrow or "--o" in arrow:
                rel_type = "aggregation"
            elif "..>" in arrow or "<.." in arrow:
                rel_type = "dependency"

            # Ensure entities exist for both ends
            if from_id not in entities_by_id:
                entities_by_id[from_id] = DiagramEntity(
                    id=from_id,
                    name=from_id,
                    type="class",
                    attributes=[],
                    methods=[],
                )
            if to_id not in entities_by_id:
                entities_by_id[to_id] = DiagramEntity(
                    id=to_id,
                    name=to_id,
                    type="class",
                    attributes=[],
                    methods=[],
                )

            relationships.append(
                DiagramRelationship(
                    from_id=from_id,
                    to_id=to_id,
                    type=rel_type,
                    label=label.strip() if label else None,
                    fromLabel=from_mult if from_mult else None,
                    toLabel=to_mult if to_mult else None,
                )
            )
            continue

        # ERD crow's foot relationships
        m_erd_rel = erd_rel_re.match(line)
        if m_erd_rel:
            from_id, crow_foot, to_id, label = m_erd_rel.groups()

            # Map crow's foot notation to cardinality
            # ||..|| = 1:1
            # ||..|{ = 1:N
            # }|..|{ = N:M
            rel_type = "1:N"  # default
            if "||..||" in crow_foot:
                rel_type = "1:1"
            elif "||..|{" in crow_foot or "}..||" in crow_foot:
                rel_type = "1:N"
            elif "}|..|{" in crow_foot or "{|..|}" in crow_foot:
                rel_type = "N:M"

            # Ensure entities exist for both ends
            if from_id not in entities_by_id:
                entities_by_id[from_id] = DiagramEntity(
                    id=from_id,
                    name=from_id,
                    type="table",
                    attributes=[],
                    methods=[],
                )
            if to_id not in entities_by_id:
                entities_by_id[to_id] = DiagramEntity(
                    id=to_id,
                    name=to_id,
                    type="table",
                    attributes=[],
                    methods=[],
                )

            relationships.append(
                DiagramRelationship(
                    from_id=from_id,
                    to_id=to_id,
                    type=rel_type,
                    label=label.strip() if label else None,
                )
            )

    # Make sure any open class is flushed
    flush_current_entity()

    return DiagramModel(
        entities=list(entities_by_id.values()),
        relationships=relationships,
    )


@router.post("/generate", response_model=DiagramResponse)
async def generate_diagram(request: DiagramRequest):
    """Generate diagram using AI analysis."""
    try:
        print(f"Generating {request.diagram_type} diagram for: {request.description[:100]}...")
        
        # Choose diagram type if auto_choose is enabled
        diagram_type = request.diagram_type
        if request.auto_choose:
            description_lower = request.description.lower()
            if any(word in description_lower for word in ['sequence', 'flow', 'interaction', 'message', 'call', 'request']):
                diagram_type = "sequence"
            elif any(word in description_lower for word in ['use case', 'actor', 'scenario', 'user story', 'requirement']):
                diagram_type = "usecase"
            else:
                diagram_type = "class"
        
        # 1. Parallelize analysis and code generation for all diagram types
        analysis_data = None
        
        # Define the analysis task based on type
        async def get_analysis():
            if diagram_type == "class":
                from ..analyzers.class_analyzer import analyze_for_class_diagram
                return await analyze_for_class_diagram(request.description)
            elif diagram_type == "usecase":
                from ..analyzers.usecase_analyzer import analyze_for_usecase_diagram
                return await analyze_for_usecase_diagram(request.description)
            elif diagram_type == "erd":
                from ..analyzers.erd_analyzer import analyze_for_erd
                return await analyze_for_erd(request.description)
            elif diagram_type == "sequence":
                from ..analyzers.sequence_analyzer import analyze_for_sequence_diagram
                return await analyze_for_sequence_diagram(request.description)
            return None

        # Start both tasks concurrently
        print(f"[API] Starting parallel tasks for {diagram_type} diagram...")
        analysis_task = asyncio.create_task(get_analysis())
        code_task = asyncio.create_task(generate_code(request.description, request.language, diagram_type))
        
        # Wait for both to complete
        analysis_data, generated_code = await asyncio.gather(analysis_task, code_task)

        # 2. Generate PlantUML code using the analysis
        plantuml_code = await generate_plantuml_code(
            request.description, 
            diagram_type, 
            request.include_relations,
            analysis=analysis_data
        )
        
        # Encode PlantUML for URL
        encoded = encode_plantuml(plantuml_code)
        
        # Render to PNG
        png_base64 = render_plantuml_to_png(plantuml_code)
        
        # 3. Prepare Model using the SAME analysis data
        diagram_model = None
        try:
            if diagram_type == "class" and analysis_data:
                entities = []
                name_to_id = {}
                for cls in analysis_data.get("classes", []):
                    entity = DiagramEntity(
                        name=cls["name"],
                        type="class",
                        attributes=cls.get("attributes", []),
                        methods=cls.get("methods", [])
                    )
                    entities.append(entity)
                    name_to_id[cls["name"]] = entity.id
                    
                relationships = []
                for rel in analysis_data.get("relationships", []):
                    from_id = name_to_id.get(rel["from"])
                    to_id = name_to_id.get(rel["to"])
                    if from_id and to_id:
                        relationships.append(DiagramRelationship(
                            from_id=from_id,
                            to_id=to_id,
                            type=rel.get("type", "association"),
                            label=rel.get("label", "")
                        ))
                diagram_model = DiagramModel(entities=entities, relationships=relationships)
                
            elif diagram_type == "usecase" and analysis_data:
                entities = []
                name_to_id = {}
                # Add actors
                for actor in analysis_data.get("actors", []):
                    entity = DiagramEntity(name=actor["name"], type="actor")
                    entities.append(entity)
                    name_to_id[actor["name"]] = entity.id
                # Add use cases
                for uc in analysis_data.get("use_cases", []):
                    entity = DiagramEntity(name=uc["name"], type="usecase")
                    entities.append(entity)
                    name_to_id[uc["name"]] = entity.id
                
                relationships = []
                # Actor to Use Case associations
                for assoc in analysis_data.get("associations", []):
                    from_id = name_to_id.get(assoc["actor"])
                    to_id = name_to_id.get(assoc["use_case"])
                    if from_id and to_id:
                        relationships.append(DiagramRelationship(from_id=from_id, to_id=to_id, type="association"))
                # Use Case to Use Case relationships (include/extend)
                for rel in analysis_data.get("relationships", []):
                    from_id = name_to_id.get(rel["from"])
                    to_id = name_to_id.get(rel["to"])
                    if from_id and to_id:
                        relationships.append(DiagramRelationship(from_id=from_id, to_id=to_id, type=rel.get("type", "dependency"), label=rel.get("type")))
                
                diagram_model = DiagramModel(entities=entities, relationships=relationships)

            elif diagram_type == "erd" and analysis_data:
                entities = []
                name_to_id = {}
                for ent in analysis_data.get("entities", []):
                    attrs = [f"{a['name']}: {a['type']}{' [PK]' if a.get('pk') else ''}{' [FK]' if a.get('fk') else ''}" for a in ent.get("attributes", [])]
                    entity = DiagramEntity(name=ent["name"], type="table", attributes=attrs)
                    entities.append(entity)
                    name_to_id[ent["name"]] = entity.id
                
                relationships = []
                for rel in analysis_data.get("relationships", []):
                    from_id = name_to_id.get(rel["from"])
                    to_id = name_to_id.get(rel["to"])
                    if from_id and to_id:
                        relationships.append(DiagramRelationship(
                            from_id=from_id, 
                            to_id=to_id, 
                            type=rel.get("cardinality", "1:N"),
                            label=rel.get("label", "")
                        ))
                diagram_model = DiagramModel(entities=entities, relationships=relationships)

        except Exception as model_err:
            print(traceback.format_exc())
            print(f"Warning: Model generation failed, but PlantUML succeeded: {model_err}")

        # If analyzers didn't produce a model (e.g. sequence diagrams, or analyzer failed),
        # fall back to parsing the already-generated PlantUML so the editor still
        # gets entities + relationships.
        if diagram_model is None and request.include_relations:
            try:
                diagram_model = _parse_plantuml_to_model(plantuml_code)
            except Exception as parse_err:
                print("Fallback parse_plantuml_to_model failed:", parse_err)

        return DiagramResponse(
            diagram_source=plantuml_code,
            generated_code=generated_code,
            diagram_png_base64=png_base64,
            encoded_plantuml=encoded,
            diagram_model=diagram_model
        )
        
    except Exception as e:
        print(f"Error in generate_diagram: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating diagram: {str(e)}")


@router.post("/render")
async def render_diagram(request: RenderRequest):
    """Render PlantUML code directly to PNG."""
    try:
        if not request.plantuml_code or not request.plantuml_code.strip():
            raise HTTPException(status_code=400, detail="PlantUML code is required")

        # Encode PlantUML for URL
        encoded = encode_plantuml(request.plantuml_code)
        
        # Render to PNG
        png_base64 = render_plantuml_to_png(request.plantuml_code)
        
        return {
            "diagram_png_base64": png_base64,
            "encoded_plantuml": encoded
        }
    except Exception as e:
        print(f"Error in render_diagram: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error rendering diagram: {str(e)}")


@router.post("/parse-plantuml-to-model", response_model=DiagramModel)
async def parse_plantuml_to_model_endpoint(request: ParsePlantUMLRequest):
    """
    Parse PlantUML text back into a DiagramModel so that
    the visual editors can stay in sync with manually-edited diagrams.
    """
    try:
        if not request.plantuml_code or not request.plantuml_code.strip():
            raise HTTPException(status_code=400, detail="PlantUML code is required")
        return _parse_plantuml_to_model(request.plantuml_code)
    except HTTPException:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        print("Error in parse_plantuml_to_model:", str(e))
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error parsing PlantUML: {str(e)}")


@router.post("/generate-model")
async def generate_model(request: GenerateModelRequest):
    """Generate structured diagram model using AI analysis."""
    try:
        # 1. Analyze
        if request.diagram_type == "class":
            from ..analyzers.class_analyzer import analyze_for_class_diagram
            raw_data = analyze_for_class_diagram(request.description)
            
            # 2. Convert to DiagramModel
            entities = []
            name_to_id = {}
            
            for cls in raw_data.get("classes", []):
                # Create entity with UUID
                entity = DiagramEntity(
                    name=cls["name"],
                    type="class",
                    attributes=cls.get("attributes", []),
                    methods=cls.get("methods", [])
                )
                entities.append(entity)
                name_to_id[cls["name"]] = entity.id
                
            relationships = []
            for rel in raw_data.get("relationships", []):
                # Map names to IDs
                from_id = name_to_id.get(rel["from"])
                to_id = name_to_id.get(rel["to"])
                
                if from_id and to_id:
                    relationships.append(DiagramRelationship(
                        from_id=from_id, # Pydantic alias 'from'
                        to_id=to_id,     # Pydantic alias 'to'
                        type=rel.get("type", "association"),
                        label=rel.get("label")
                    ))
            
            return DiagramModel(entities=entities, relationships=relationships)
        else:
            # Fallback for other types or TODO
            raise HTTPException(status_code=400, detail="Only class diagrams supported for Model mode currently")
            
    except Exception as e:
        print(f"Error in generate_model: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error generating model: {str(e)}")


@router.post("/render-model")
async def render_model_endpoint(request: RenderModelRequest):
    """Render diagram from structured model."""
    try:
        plantuml_code = generate_plantuml_from_model(request.model)
        
        # Render to PNG
        png_base64 = render_plantuml_to_png(plantuml_code)
        encoded = encode_plantuml(plantuml_code)
        
        return {
            "diagram_source": plantuml_code,
            "diagram_png_base64": png_base64,
            "encoded_plantuml": encoded
        }
    except Exception as e:
        print(f"Error in render_model: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error rendering model: {str(e)}")


@router.get("/diagram-types")
async def get_diagram_types():
    """Get available diagram types."""
    return {
        "available_types": [
            {"type": "class", "description": "Class diagrams showing structure"},
            {"type": "sequence", "description": "Sequence diagrams showing interactions"},
            {"type": "usecase", "description": "Use case diagrams showing functionality"},
            {"type": "erd", "description": "ERD showing database structure"}
        ],
        "default": "class"
    }
