"""
ERD Analyzer - Analyzes descriptions for Entity Relationship Diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json


def normalize_erd_analysis(data: Dict) -> Dict:
    """Validate and normalize ERD metadata, ensuring no orphan entities with smart relationship inference."""
    entities = {}
    for e in data.get("entities", []):
        name = e.get("name")
        if name:
            # Ensure entity has proper attributes structure
            attributes = []
            for attr in e.get("attributes", []):
                if isinstance(attr, dict):
                    attributes.append(attr)
                else:
                    attributes.append({"name": str(attr), "type": "text", "pk": False, "fk": False})
            
            # Ensure at least an id attribute exists
            if not any(a.get("pk") for a in attributes):
                attributes.insert(0, {"name": "id", "type": "int", "pk": True, "fk": False})
            
            entities[name] = {
                "name": name,
                "attributes": attributes
            }
    
    valid_relationships = []
    connected_entities = set()
    existing_pairs = set()  # Track (from, to) pairs to avoid duplicates
    
    for rel in data.get("relationships", []):
        from_ent = rel.get("from")
        to_ent = rel.get("to")
        if from_ent in entities and to_ent in entities:
            pair = (from_ent, to_ent)
            reverse_pair = (to_ent, from_ent)
            if pair not in existing_pairs and reverse_pair not in existing_pairs:
                # Normalize cardinality to standard Crow's foot patterns if needed
                card = rel.get("cardinality", "1:N")
                if card not in ["1:1", "1:N", "N:M"]:
                    card = "1:N"
                rel["cardinality"] = card
                valid_relationships.append(rel)
                connected_entities.add(from_ent)
                connected_entities.add(to_ent)
                existing_pairs.add(pair)
    
    # Smart relationship inference from FK attributes
    entity_names_lower = {name.lower(): name for name in entities.keys()}
    
    for entity_name, entity_data in entities.items():
        for attr in entity_data.get("attributes", []):
            attr_name = attr.get("name", "").lower()
            # Look for FK patterns like "customer_id", "order_id", etc.
            if attr_name.endswith("_id") and attr.get("fk"):
                # Extract the referenced entity name
                ref_name = attr_name[:-3]  # Remove "_id"
                # Try to find matching entity
                if ref_name in entity_names_lower:
                    target_entity = entity_names_lower[ref_name]
                    pair = (target_entity, entity_name)
                    reverse_pair = (entity_name, target_entity)
                    if pair not in existing_pairs and reverse_pair not in existing_pairs:
                        valid_relationships.append({
                            "from": target_entity,
                            "to": entity_name,
                            "cardinality": "1:N",
                            "label": "has"
                        })
                        connected_entities.add(target_entity)
                        connected_entities.add(entity_name)
                        existing_pairs.add(pair)
    
    # Find remaining orphan entities
    entity_names = list(entities.keys())
    orphans = [name for name in entity_names if name not in connected_entities]
    
    # Try semantic matching for orphans based on common patterns
    semantic_groups = {
        "order": ["orderitem", "orderdetail", "payment", "shipping", "invoice"],
        "customer": ["order", "cart", "address", "review"],
        "product": ["orderitem", "cartitem", "inventory", "review", "category"],
        "user": ["order", "cart", "profile", "address", "review"],
        "student": ["enrollment", "grade", "attendance"],
        "course": ["enrollment", "lesson", "assignment", "schedule"],
        "employee": ["department", "salary", "attendance", "project"],
        "department": ["employee"],
        "patient": ["appointment", "prescription", "medicalrecord", "billing"],
        "doctor": ["appointment", "prescription"],
    }
    
    for orphan in orphans[:]:  # Use slice copy to allow modification
        orphan_lower = orphan.lower()
        # Check if orphan can be a parent or child in semantic groups
        found_match = False
        
        # Check if orphan is a parent type
        if orphan_lower in semantic_groups:
            for child_type in semantic_groups[orphan_lower]:
                for ent_name in entities.keys():
                    if child_type in ent_name.lower() and ent_name != orphan:
                        pair = (orphan, ent_name)
                        if pair not in existing_pairs and (ent_name, orphan) not in existing_pairs:
                            valid_relationships.append({
                                "from": orphan,
                                "to": ent_name,
                                "cardinality": "1:N",
                                "label": "has"
                            })
                            connected_entities.add(orphan)
                            connected_entities.add(ent_name)
                            existing_pairs.add(pair)
                            found_match = True
                            break
                if found_match:
                    break
        
        # Check if orphan matches as a child type
        if not found_match:
            for parent_type, children in semantic_groups.items():
                if any(child in orphan_lower for child in children) or orphan_lower in children:
                    for ent_name in entities.keys():
                        if parent_type in ent_name.lower() and ent_name != orphan:
                            pair = (ent_name, orphan)
                            if pair not in existing_pairs and (orphan, ent_name) not in existing_pairs:
                                valid_relationships.append({
                                    "from": ent_name,
                                    "to": orphan,
                                    "cardinality": "1:N",
                                    "label": "has"
                                })
                                connected_entities.add(orphan)
                                connected_entities.add(ent_name)
                                existing_pairs.add(pair)
                                found_match = True
                                break
                    if found_match:
                        break
    
    # Final check for any remaining orphans - connect to first entity only if truly disconnected
    orphans = [name for name in entity_names if name not in connected_entities]
    if orphans and connected_entities:
        first_connected = list(connected_entities)[0]
        for orphan in orphans:
            pair = (first_connected, orphan)
            if pair not in existing_pairs and (orphan, first_connected) not in existing_pairs:
                valid_relationships.append({
                    "from": first_connected,
                    "to": orphan,
                    "cardinality": "1:N",
                    "label": "related_to"
                })
                existing_pairs.add(pair)
            
    return {
        "entities": list(entities.values()),
        "relationships": valid_relationships,
        "title": data.get("title", "Database Schema")
    }


async def analyze_for_erd(description: str) -> Dict:
    """Analyze description for ERD using AI."""
    prompt = f"""
Return valid JSON representing an Entity Relationship Diagram (ERD) for this description: "{description}"

STRUCTURE:
{{
  "title": "Title",
  "entities": [{{
    "name": "Name",
    "attributes": [
      {{ "name": "id", "type": "int", "pk": true, "fk": false }},
      {{ "name": "ref_id", "type": "int", "pk": false, "fk": true }}
    ]
  }}],
  "relationships": [{{ "from": "A", "to": "B", "cardinality": "1:1|1:N|N:M", "label": "verb" }}]
}}

STRICT RULES:
1. Relationships: Every entity MUST have at least one relationship. No orphans.
2. Cardinality: Use "1:N" for parent-child (Order has Items), "N:M" for associations (Student-Course).
3. Attributes: Include FK attributes for "to" side of 1:N relationships.
4. Labels: Use short verbs (e.g., "contains", "places").
"""
    
    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)
    
    try:
        data = json.loads(json_str)
        return normalize_erd_analysis(data)
    except json.JSONDecodeError:
        return {
            "title": "Error ERD",
            "entities": [{"name": "Entity", "attributes": [{"name": "id", "type": "number", "pk": True, "fk": False}]}],
            "relationships": []
        }
