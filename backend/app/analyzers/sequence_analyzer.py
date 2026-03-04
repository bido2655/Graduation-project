"""
Sequence Diagram Analyzer - Analyzes descriptions for sequence diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json


def normalize_sequence_analysis(data: Dict) -> Dict:
    """Validate and normalize sequence diagram metadata."""
    participants = {p["name"]: p for p in data.get("participants", [])}

    # Normalize top-level interactions (flat legacy format)
    valid_interactions = []
    for interaction in data.get("interactions", []):
        if interaction.get("from") in participants and interaction.get("to") in participants:
            valid_interactions.append(interaction)

    # Normalize groups
    valid_groups = []
    for group in data.get("groups", []):
        group_interactions = []
        for interaction in group.get("interactions", []):
            if interaction.get("from") in participants and interaction.get("to") in participants:
                group_interactions.append(interaction)
        if group_interactions:
            valid_groups.append({
                "name": group.get("name", "Section"),
                "interactions": group_interactions
            })

    # Normalize alt blocks
    valid_alt_blocks = []
    for alt in data.get("alt_blocks", []):
        main_interactions = []
        for interaction in alt.get("interactions", []):
            if interaction.get("from") in participants and interaction.get("to") in participants:
                main_interactions.append(interaction)
        else_interactions = []
        for interaction in alt.get("else_interactions", []):
            if interaction.get("from") in participants and interaction.get("to") in participants:
                else_interactions.append(interaction)
        if main_interactions:
            valid_alt_blocks.append({
                "condition": alt.get("condition", "Condition"),
                "interactions": main_interactions,
                "else_label": alt.get("else_label", ""),
                "else_interactions": else_interactions
            })

    return {
        "participants": list(participants.values()),
        "interactions": valid_interactions,
        "groups": valid_groups,
        "alt_blocks": valid_alt_blocks
    }


async def analyze_for_sequence_diagram(description: str) -> Dict:
    """Analyze description for sequence diagram using AI with emphasis on interactions."""
    prompt = f"""
Return valid JSON for a Sequence diagram: "{description}"

STRUCTURE:
{{
  "participants": [{{ "name": "Name", "type": "actor|participant|database|boundary|control|entity" }}],
  "groups": [
    {{
      "name": "SectionName",
      "interactions": [{{ "from": "A", "to": "B", "message": "msg", "type": "sync|async|return" }}]
    }}
  ],
  "alt_blocks": [
    {{
      "condition": "ConditionLabel",
      "interactions": [{{ "from": "A", "to": "B", "message": "msg", "type": "sync|async|return" }}],
      "else_label": "ElseLabel",
      "else_interactions": [{{ "from": "A", "to": "B", "message": "msg", "type": "sync|async|return" }}]
    }}
  ]
}}

RULES:
1. Max 8 participants. Use appropriate types:
   - "actor" for human users/external actors
   - "participant" for system components, services, controllers
   - "database" for databases, data stores
   - "boundary" for UI/API boundaries
   - "control" for controllers, managers
   - "entity" for domain entities, business objects
2. EVERY participant MUST appear in at least one interaction.
3. Include return messages for sync calls (type "return").
4. Group related interactions into logical "groups" with descriptive names (e.g. "Login", "Browse Menu", "Place Order").
5. Use "alt_blocks" for conditional flows (success/failure, valid/invalid, etc.).
6. Participant names MUST match the participant list exactly.
7. Place alt_blocks AFTER all groups. They should represent decision points.
8. Return ONLY valid JSON, no extra text.
"""

    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)

    try:
        data = json.loads(json_str)
        return normalize_sequence_analysis(data)
    except json.JSONDecodeError:
        return {
            "participants": [
                {"name": "User", "type": "actor"},
                {"name": "System", "type": "participant"}
            ],
            "interactions": [
                {"from": "User", "to": "System", "message": "request", "type": "sync"},
                {"from": "System", "to": "User", "message": "response", "type": "return"}
            ],
            "groups": [],
            "alt_blocks": []
        }
