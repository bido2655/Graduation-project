"""
ERD Generator - Generates PlantUML Entity Relationship Diagrams.
"""
from typing import Dict


def generate_erd_diagram(data: Dict) -> str:
    """Generate PlantUML ERD from AI analysis in a specific modern style."""
    plantuml = """@startuml

' hide the spot
' hide circle

' avoid problems with angled crows feet
skinparam linetype ortho

"""
    title = data.get("title", "Entity Relationship Diagram")
    plantuml += f"title {title}\n\n"
    
    # Map entities to aliases (e01, e02, etc.)
    entity_map = {}
    for i, entity in enumerate(data.get("entities", []), 1):
        alias = f"e{i:02d}"
        entity_name = entity['name']
        entity_map[entity_name] = alias
        
        plantuml += f'entity "{entity_name}" as {alias} {{\n'
        
        # Split attributes into PKs and others
        attributes = entity.get("attributes", [])
        pks = [a for a in attributes if a.get("pk")]
        others = [a for a in attributes if not a.get("pk")]
        
        for attr in pks:
            name = attr.get("name", "id")
            atype = attr.get("type", "number")
            plantuml += f"  *{name} : {atype} <<generated>>\n"
            
        if pks and others:
            plantuml += "  --\n"
            
        for attr in others:
            name = attr.get("name", "attr")
            atype = attr.get("type", "text")
            marker = "*" if attr.get("fk") else ""
            fk_label = " <<FK>>" if attr.get("fk") else ""
            plantuml += f"  {marker}{name} : {atype}{fk_label}\n"
            
        plantuml += "}\n\n"
        
    for rel in data.get("relationships", []):
        card = rel.get("cardinality", "1:N")
        from_ent = rel['from']
        to_ent = rel['to']
        
        from_alias = entity_map.get(from_ent)
        to_alias = entity_map.get(to_ent)
        
        if not from_alias or not to_alias:
            continue
            
        label = f" : {rel.get('label', '')}" if rel.get("label") else ""
        
        # Map to Crow's foot notation
        if card == "1:1":
            plantuml += f"{from_alias} ||..|| {to_alias}{label}\n"
        elif card == "1:N":
            plantuml += f"{from_alias} ||..|{{ {to_alias}{label}\n"
        elif card == "N:M":
            plantuml += f"{from_alias} }}|..|{{ {to_alias}{label}\n"
        else:
            plantuml += f"{from_alias} -- {to_alias}{label}\n"
            
    plantuml += "\n@enduml"
    return plantuml
