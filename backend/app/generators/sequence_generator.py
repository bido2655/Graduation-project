"""
Sequence Diagram Generator - Generates PlantUML sequence diagrams.
"""
import re
from typing import Dict, List, Optional


def sanitize_name(name: str, existing_map: Dict) -> str:
    """Sanitize participant names for PlantUML."""
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.strip())
    if not safe_name:
        safe_name = "Participant"
    elif not safe_name[0].isalpha():
        safe_name = 'P' + safe_name
    
    original_safe = safe_name
    counter = 1
    while safe_name in existing_map.values():
        safe_name = f"{original_safe}{counter}"
        counter += 1
    
    return safe_name


def find_matching_name(name: str, participant_map: Dict) -> Optional[str]:
    """Find matching participant name with case-insensitive search."""
    if name in participant_map:
        return participant_map[name]
    
    for original_name, safe_name in participant_map.items():
        if original_name.lower() == name.lower():
            return safe_name
    
    return None


def _render_interaction(interaction: Dict, participant_map: Dict, safe_names: List[str], indent: str = "") -> str:
    """Render a single interaction line."""
    raw_from = interaction.get('from', '')
    raw_to = interaction.get('to', '')
    raw_message = interaction.get('message', 'interaction')

    # Safely convert to string in case the AI returned a dict
    from_name = str(raw_from).strip() if not isinstance(raw_from, str) else raw_from.strip()
    to_name = str(raw_to).strip() if not isinstance(raw_to, str) else raw_to.strip()
    message = str(raw_message).strip() if not isinstance(raw_message, str) else raw_message.strip()

    from_safe = find_matching_name(from_name, participant_map)
    to_safe = find_matching_name(to_name, participant_map)

    if not from_safe and safe_names:
        from_safe = safe_names[0]
    if not to_safe and safe_names:
        to_safe = safe_names[-1] if len(safe_names) > 1 else safe_names[0]

    arrow_map = {
        "sync": "->",
        "async": "->>",
        "return": "-->"
    }
    arrow = arrow_map.get(interaction.get("type", "sync"), "->")

    return f"{indent}{from_safe} {arrow} {to_safe} : {message}\n"


def _render_interactions(interactions: List[Dict], participant_map: Dict, safe_names: List[str], indent: str = "") -> str:
    """Render a list of interactions."""
    result = ""
    for interaction in interactions:
        result += _render_interaction(interaction, participant_map, safe_names, indent)
    return result


def generate_sequence_diagram(data: Dict) -> str:
    """Generate PlantUML sequence diagram from AI analysis."""
    plantuml = """@startuml
!theme plain
skinparam sequence {
  ParticipantBackgroundColor #3b82f6
  ParticipantBorderColor #1e40af
  LifeLineBackgroundColor #0f172a
  LifeLineBorderColor #334155
  ArrowColor #60a5fa
  FontColor #f8fafc
}

"""
    
    participants = data.get("participants", [])
    if not participants:
        participants = [
            {"name": "User", "type": "actor"},
            {"name": "System", "type": "participant"}
        ]
    
    participant_map = {}
    safe_names = []
    
    for i, participant in enumerate(participants):
        original_name = participant.get('name', f'Participant{i}').strip()
        safe_name = sanitize_name(original_name, participant_map)
        participant_map[original_name] = safe_name
        safe_names.append(safe_name)
        
        p_type = participant.get("type", "participant").lower()
        display_name = f'"{original_name}"'
        
        if p_type == "actor":
            plantuml += f"actor {display_name} as {safe_name}\n"
        elif p_type == "database":
            plantuml += f"database {display_name} as {safe_name}\n"
        elif p_type == "boundary":
            plantuml += f"boundary {display_name} as {safe_name}\n"
        elif p_type == "control":
            plantuml += f"control {display_name} as {safe_name}\n"
        elif p_type == "entity":
            plantuml += f"entity {display_name} as {safe_name}\n"
        else:
            plantuml += f"participant {display_name} as {safe_name}\n"
    
    plantuml += "\n"
    
    # --- Render groups (== SectionName ==) ---
    groups = data.get("groups", [])
    if groups:
        for group in groups:
            group_name = group.get("name", "Section")
            plantuml += f"== {group_name} ==\n"
            plantuml += _render_interactions(
                group.get("interactions", []),
                participant_map, safe_names
            )
            plantuml += "\n"
    
    # --- Render alt blocks (alt / else / end) ---
    alt_blocks = data.get("alt_blocks", [])
    if alt_blocks:
        for alt in alt_blocks:
            condition = alt.get("condition", "Condition")
            plantuml += f"alt {condition}\n"
            plantuml += _render_interactions(
                alt.get("interactions", []),
                participant_map, safe_names, indent="    "
            )
            
            else_label = alt.get("else_label", "")
            else_interactions = alt.get("else_interactions", [])
            if else_label or else_interactions:
                plantuml += f"else {else_label}\n"
                plantuml += _render_interactions(
                    else_interactions,
                    participant_map, safe_names, indent="    "
                )
            
            plantuml += "end\n\n"
    
    # --- Fallback: render flat interactions if no groups/alt_blocks ---
    if not groups and not alt_blocks:
        interactions = data.get("interactions", [])
        if not interactions and len(safe_names) >= 2:
            plantuml += f"{safe_names[0]} -> {safe_names[1]} : request\n"
            plantuml += f"{safe_names[1]} --> {safe_names[0]} : response\n"
        else:
            plantuml += _render_interactions(interactions, participant_map, safe_names)
    
    plantuml += "@enduml"
    return plantuml
