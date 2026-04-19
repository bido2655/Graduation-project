"""
BPMN Diagram Generator - Generates PlantUML Activity diagrams mapped to BPMN processes.
Specifically uses Activity Diagram beta formatting with swimlanes.
"""
from typing import Dict, List, Any


def render_bpmn_steps(steps: List[Dict], current_swimlane: str = "", indent: str = "") -> tuple[str, str]:
    """Recursively render BPMN steps and keep track of current swimlane."""
    plantuml = ""
    for step in steps:
        if isinstance(step, str):
            plantuml += f"{indent}:{step};\n"
            continue
            
        target_swimlane = step.get("swimlane")
        if target_swimlane and target_swimlane != current_swimlane:
            # Switch to requested swimlane
            plantuml += f"{indent}|{target_swimlane}|\n"
            current_swimlane = target_swimlane
            
        step_type = step.get("type", "task").lower()
        
        if step_type == "task":
            name = step.get("name", "Unnamed Task")
            plantuml += f"{indent}:{name};\n"
            
        elif step_type == "gateway":
            condition = step.get("condition", step.get("name", "Gateway"))
            yes_branch = step.get("yes", step.get("true_branch", []))
            no_branch = step.get("no", step.get("false_branch", []))
            
            plantuml += f"{indent}if ({condition}) then (yes)\n"
            p_add, current_swimlane = render_bpmn_steps(yes_branch, current_swimlane, indent + "  ")
            plantuml += p_add
            
            if no_branch:
                plantuml += f"{indent}else (no)\n"
                p_add, current_swimlane = render_bpmn_steps(no_branch, current_swimlane, indent + "  ")
                plantuml += p_add
                
            plantuml += f"{indent}endif\n"
            
        elif step_type == "parallel_gateway":
            branches = step.get("branches", [])
            if branches:
                plantuml += f"{indent}fork\n"
                for i, branch in enumerate(branches):
                    if i > 0:
                        plantuml += f"{indent}fork again\n"
                    p_add, current_swimlane = render_bpmn_steps(branch, current_swimlane, indent + "  ")
                    plantuml += p_add
                plantuml += f"{indent}end fork\n"
                
        elif step_type == "event":
            event_type = step.get("event_type", "intermediate").lower()
            name = step.get("name", "")
            
            if event_type == "start":
                plantuml += f"{indent}start\n"
                if name:
                    plantuml += f"{indent}note right: {name}\n"
            elif event_type in ["end", "stop"]:
                if name:
                    plantuml += f"{indent}note right: {name}\n"
                plantuml += f"{indent}stop\n"
            else:
                # Intermediate event
                if name:
                    plantuml += f"{indent}:{name} <Event>;\n"
                else:
                    plantuml += f"{indent}:<Event>;\n"
                
        elif step_type == "note":
            text = step.get("text", "")
            position = step.get("position", "right")
            plantuml += f"{indent}note {position}\n{indent}  {text}\n{indent}end note\n"
            
        else:
            # Fallback for generic steps
            name = step.get("name", str(step))
            plantuml += f"{indent}:{name};\n"
            
    return plantuml, current_swimlane


def generate_bpmn_diagram(data: Dict) -> str:
    """Generate PlantUML diagram from AI analysis for BPMN structure."""
    plantuml = "@startuml\n!theme plain\n"
    
    # Generic skinparam for clean output
    plantuml += "skinparam activity {\n"
    plantuml += "  BackgroundColor #3b82f6\n"
    plantuml += "  BorderColor #1e40af\n"
    plantuml += "  FontColor #f8fafc\n"
    plantuml += "  ArrowColor #60a5fa\n"
    plantuml += "}\n\n"
    
    title = data.get("title")
    if title:
        plantuml += f"title {title}\n\n"
        
    swimlanes = data.get("swimlanes", [])
    if swimlanes:
        for lane in swimlanes:
            color = lane.get("color", "")
            name = lane.get("name", "Swimlane")
            if color:
                plantuml += f"|{color}|{name}|\n"
            else:
                plantuml += f"|{name}|\n"
        plantuml += "\n"
        
    activities = data.get("activities", data.get("steps", []))
    
    # Generate fallback if empty
    if not activities:
        activities = [
            {"type": "event", "event_type": "start", "name": "Start Process"},
            {"type": "task", "name": "Review Request"},
            {"type": "event", "event_type": "end", "name": "End Process"}
        ]
        
    p_add, _ = render_bpmn_steps(activities, "", "")
    plantuml += p_add
    
    plantuml += "@enduml"
    return plantuml
