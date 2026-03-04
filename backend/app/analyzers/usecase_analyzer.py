"""
Use Case Diagram Analyzer - Analyzes descriptions for use case diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json


def normalize_usecase_analysis(data: Dict) -> Dict:
    """Validate and normalize use case diagram metadata."""
    # Normalize actors - convert list of dicts to a map for easy lookup
    actors_data = data.get("actors", [])
    if actors_data and isinstance(actors_data[0], str):
        # Fallback for old format
        actors = {name: {"name": name, "role": "primary"} for name in actors_data}
    else:
        actors = {a["name"]: a for a in actors_data}
    
    use_cases = {uc["name"]: uc for uc in data.get("use_cases", [])}
    
    valid_associations = []
    for assoc in data.get("associations", []):
        if assoc.get("actor") in actors and assoc.get("use_case") in use_cases:
            valid_associations.append(assoc)
            
    valid_relationships = []
    for rel in data.get("relationships", []):
        if rel.get("from") in use_cases and rel.get("to") in use_cases:
            valid_relationships.append(rel)
            
    return {
        "actors": list(actors.values()),
        "use_cases": list(use_cases.values()),
        "associations": valid_associations,
        "relationships": valid_relationships,
        "system_name": data.get("system_name", "System Boundary")
    }


async def analyze_for_usecase_diagram(description: str) -> Dict:
    """Analyze description for use case diagram using AI with emphasis on relationships."""
    prompt = f"""
Return valid JSON for a Use Case diagram: "{description}"

STRUCTURE:
{{
  "system_name": "Name",
  "actors": [{{ "name": "Name", "role": "primary|secondary" }}],
  "use_cases": [{{ "name": "UC Name", "description": "desc" }}],
  "associations": [{{ "actor": "ActorName", "use_case": "UCName" }}],
  "relationships": [{{ "from": "UC1", "to": "UC2", "type": "include|extend|generalization" }}]
}}

RULES:
1. role: "primary" (left) for users; "secondary" (right) for external systems (DB, Payment).
2. Max 5 actors, 10 use cases.
3. Every use case must link to at least one actor.
"""
    
    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)
    
    try:
        data = json.loads(json_str)
        return normalize_usecase_analysis(data)
    except json.JSONDecodeError:
        return {
            "actors": [{"name": "User", "role": "primary"}],
            "use_cases": [{"name": "Use System", "description": "Use the system"}],
            "associations": [{"actor": "User", "use_case": "Use System"}],
            "relationships": []
        }
