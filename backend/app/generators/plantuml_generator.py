from app.models.diagram_model import DiagramModel


def _sanitize_alias(raw_id: str) -> str:
    """Convert a UUID (or any string) into a valid PlantUML alias.
    
    PlantUML aliases must be unquoted identifiers with no hyphens.
    We replace hyphens with underscores and prefix with 'e_' to ensure
    the alias starts with a letter.
    """
    return "e_" + raw_id.replace("-", "_")


def generate_plantuml_from_model(model: DiagramModel) -> str:
    """Generates PlantUML code from a structured DiagramModel."""
    plantuml = [
        "@startuml", 
        "!theme plain", 
        "skinparam class {", 
        "  BackgroundColor #f0fdfa", 
        "  BorderColor #2dd4bf", 
        "  ArrowColor #f43f5e", 
        "  FontColor #134e4a", 
        "}", 
        ""
    ]
    
    # Build id -> sanitized alias mapping
    id_to_alias = {}
    for entity in model.entities:
        id_to_alias[entity.id] = _sanitize_alias(entity.id)
    
    # Process entities
    for entity in model.entities:
        alias = id_to_alias[entity.id]
        
        # BPMN Mapping
        if entity.type == 'bpmn-task':
            plantuml.append(f'rectangle "{entity.name}" as {alias} <<task>>')
        elif entity.type == 'bpmn-gateway':
            plantuml.append(f'diamond "{entity.name}" as {alias}')
        elif entity.type == 'bpmn-start':
            plantuml.append(f'circle " " as {alias} <<start>>')
        elif entity.type == 'bpmn-end':
            plantuml.append(f'circle " " as {alias} <<end>>')
            
        # Activity Diagram Mapping
        elif entity.type == 'activity-action':
            plantuml.append(f'rectangle "{entity.name}" as {alias} <<action>>')
        elif entity.type == 'activity-decision':
            plantuml.append(f'diamond "{entity.name}" as {alias}')
        elif entity.type == 'activity-initial':
            plantuml.append(f'circle " " as {alias} <<initial>>')
        elif entity.type == 'activity-final':
            plantuml.append(f'circle " " as {alias} <<final>>')
            
        # Default (Class/Table/etc.)
        else:
            plantuml.append(f'class "{entity.name}" as {alias} {{')
            for attr in entity.attributes:
                plantuml.append(f"  - {attr}")
            for method in entity.methods:
                plantuml.append(f"  + {method}")
            plantuml.append("}")
        plantuml.append("")
        
    # Process relationships (with deduplication)
    arrow_map = {
        "inheritance": "<|--",  # PlantUML standard: child <|-- parent
        "composition": "*--",
        "aggregation": "o--",
        "association": "-->",
        "dependency": "..>",
        "one-to-many": '-->',
        "many-to-many": '-->',
    }
    
    seen_rels = set()  # Track (from_id, to_id, type) to deduplicate
    
    for rel in model.relationships:
        # Skip if both ends don't have known aliases
        from_alias = id_to_alias.get(rel.from_id)
        to_alias = id_to_alias.get(rel.to_id)
        if not from_alias or not to_alias:
            continue
        
        # Deduplicate: skip if we've already seen this exact relationship
        rel_key = (rel.from_id, rel.to_id, rel.type)
        reverse_key = (rel.to_id, rel.from_id, rel.type)
        if rel_key in seen_rels or reverse_key in seen_rels:
            continue
        seen_rels.add(rel_key)
        
        # Build the arrow
        arrow = arrow_map.get(rel.type, "-->")
        
        # Build multiplicity annotations
        from_mult = ""
        to_mult = ""
        if hasattr(rel, 'fromLabel') and rel.fromLabel:
            from_mult = f' "{rel.fromLabel}"'
        if hasattr(rel, 'toLabel') and rel.toLabel:
            to_mult = f' "{rel.toLabel}"'
        
        # Build the label part
        label_part = ""
        if rel.label:
            label_part = f" : {rel.label}"
        
        # Final line: FromAlias "mult" --> "mult" ToAlias : label
        plantuml.append(f'{from_alias}{from_mult} {arrow}{to_mult} {to_alias}{label_part}')
        
    plantuml.append("@enduml")
    return "\n".join(plantuml)
