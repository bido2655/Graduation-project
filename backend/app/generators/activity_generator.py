"""
Activity Diagram Generator - Generates PlantUML activity diagrams.
"""
from typing import Dict, List, Any


def render_activity_steps(steps: List[Dict], indent: str = "") -> str:
    """Recursively render activity steps."""
    plantuml = ""
    for step in steps:
        step_type = step.get("type", "action").lower()
        
        if step_type == "action":
            name = step.get("name", "Unnamed Action")
            plantuml += f"{indent}:{name};\n"
            
        elif step_type == "condition":
            condition = step.get("condition", step.get("name", "Condition"))
            yes_branch = step.get("yes", step.get("true_branch", []))
            no_branch = step.get("no", step.get("false_branch", []))
            
            plantuml += f"{indent}if ({condition}) then (yes)\n"
            plantuml += render_activity_steps(yes_branch, indent + "  ")
            
            if no_branch:
                plantuml += f"{indent}else (no)\n"
                plantuml += render_activity_steps(no_branch, indent + "  ")
                
            plantuml += f"{indent}endif\n"
            
        elif step_type == "fork":
            branches = step.get("branches", [])
            if branches:
                plantuml += f"{indent}fork\n"
                for i, branch in enumerate(branches):
                    if i > 0:
                        plantuml += f"{indent}fork again\n"
                    plantuml += render_activity_steps(branch, indent + "  ")
                plantuml += f"{indent}end fork\n"
                
        elif step_type in ["start", "stop", "end"]:
            plantuml += f"{indent}{step_type}\n"
            
        elif step_type == "note":
            text = step.get("text", "")
            position = step.get("position", "right")
            plantuml += f"{indent}note {position}\n{indent}  {text}\n{indent}end note\n"
            
        else:
            # Fallback for generic dict structures or simple text
            name = step.get("name", str(step))
            plantuml += f"{indent}:{name};\n"
    
    return plantuml


def generate_activity_diagram(data: Dict) -> str:
    """Generate PlantUML activity diagram from AI analysis."""
    plantuml = "@startuml\n!theme plain\n"
    
    # Optional styling
    plantuml += "skinparam activity {\n"
    plantuml += "  BackgroundColor #3b82f6\n"
    plantuml += "  BorderColor #1e40af\n"
    plantuml += "  FontColor #f8fafc\n"
    plantuml += "  ArrowColor #60a5fa\n"
    plantuml += "}\n\n"
    
    title = data.get("title")
    if title:
        plantuml += f"title {title}\n\n"
        
    start_added = data.get("include_start", True)
    if start_added:
        plantuml += "start\n"
        
    activities = data.get("activities", data.get("steps", []))
    
    if not activities:
        # Fallback if no activities provided
        activities = [
            {"type": "action", "name": "Initialize"},
            {"type": "action", "name": "Process Data"},
            {"type": "action", "name": "Finalize"}
        ]
        
    plantuml += render_activity_steps(activities)
    
    end_added = data.get("include_end", data.get("include_stop", True))
    if end_added:
        plantuml += "stop\n"
        
    plantuml += "@enduml"
    return plantuml
