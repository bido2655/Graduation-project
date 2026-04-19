"""
Use Case Diagram Generator - Generates PlantUML use case diagrams.
"""
from typing import Dict


def generate_usecase_diagram(data: Dict) -> str:
    """Generate PlantUML use case diagram from AI analysis."""
    plantuml = """@startuml
!theme plain
left to right direction
skinparam usecase {
  BackgroundColor #0f172a
  BorderColor #080707
  ArrowColor #fbbf24
  FontColor #f8fafc
  FontSize 12
  StereotypeFontColor #fbbf24
}

skinparam actor {
  BorderColor #080707
  FontColor #080707
  FontSize 12
}

skinparam arrow {
  Color #080707
  FontColor #080707
}
"""
    
    all_actors = data.get("actors", [])
    primary_actors = [a for a in all_actors if a.get("role") == "primary"]
    secondary_actors = [a for a in all_actors if a.get("role") == "secondary"]
    
    # Render primary actors first (on the left)
    for actor in primary_actors:
        actor_name = actor['name']
        display_name = f'"{actor_name}"' if ' ' in actor_name else actor_name
        plantuml += f"actor {display_name}\n"
    
    plantuml += "\n"
    
    # System boundary box
    system_name = data.get("system_name", "System Boundary")
    plantuml += f'rectangle "{system_name}" {{\n'
    
    use_cases = data.get("use_cases", [])
    if not use_cases:
        use_cases = [{"name": "Use System", "description": "Use the system"}]
    
    usecase_map = {}
    for i, use_case in enumerate(use_cases):
        uc_name = use_case.get('name', f'UseCase{i}')
        uc_id = f"uc{i}"
        usecase_map[uc_name] = uc_id
        plantuml += f'  usecase "{uc_name}" as {uc_id}\n'
    
    plantuml += "}\n\n"
    
    # Render secondary actors after the rectangle (on the right)
    for actor in secondary_actors:
        actor_name = actor['name']
        display_name = f'"{actor_name}"' if ' ' in actor_name else actor_name
        plantuml += f"actor {display_name}\n"
    
    plantuml += "\n"
    
    # Associations
    actor_map = {a['name']: a for a in all_actors}
    associations = data.get("associations", [])
    
    if not associations and all_actors and use_cases:
        actor_name = all_actors[0]['name']
        actor_display = f'"{actor_name}"' if ' ' in actor_name else actor_name
        plantuml += f"{actor_display} --> {usecase_map[use_cases[0]['name']]}\n"
    else:
        for assoc in associations:
            actor_name = assoc.get('actor', 'User')
            actor_role = actor_map.get(actor_name, {}).get("role", "primary")
            actor_display = f'"{actor_name}"' if ' ' in actor_name else actor_name
            uc_name = assoc.get('use_case', '')
            uc_id = usecase_map.get(uc_name)
            
            if uc_id:
                if actor_role == "secondary":
                    # For secondary actors, draw arrow from UC to Actor to push it right
                    plantuml += f"{uc_id} --> {actor_display}\n"
                else:
                    plantuml += f"{actor_display} --> {uc_id}\n"
    
    for rel in data.get("relationships", []):
        from_name = rel.get('from', '')
        to_name = rel.get('to', '')
        from_uc = usecase_map.get(from_name)
        to_uc = usecase_map.get(to_name)
        
        if from_uc and to_uc:
            rel_type = rel.get("type", "include")
            if rel_type == "include":
                plantuml += f"{from_uc} ..> {to_uc} : <<include>>\n"
            elif rel_type == "extend":
                plantuml += f"{from_uc} ..> {to_uc} : <<extend>>\n"
            elif rel_type == "generalization":
                plantuml += f"{from_uc} <|-- {to_uc}\n"
    
    plantuml += "@enduml"
    return plantuml
