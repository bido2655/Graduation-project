"""
BPMN Diagram Analyzer - Analyzes descriptions for BPMN diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json


def normalize_bpmn_analysis(data: Dict) -> Dict:
    """Validate and normalize BPMN metadata."""
    title = data.get("title", "BPMN Diagram")
    swimlanes = data.get("swimlanes", [])
    activities = data.get("activities", [])
    
    if not isinstance(swimlanes, list):
        swimlanes = []
        
    if not isinstance(activities, list):
        activities = []
        
    return {
        "title": title,
        "swimlanes": swimlanes,
        "activities": activities
    }


async def analyze_for_bpmn_diagram(description: str) -> Dict:
    """Analyze description for BPMN diagram using AI."""
    prompt = f"""
You are an expert Business Process Model and Notation (BPMN) architect.
Your task is to analyze the user's process and map it into a strict JSON structure representing a BPMN diagram.

USER'S PROCESS DESCRIPTION:
"{description}"

YOUR INSTRUCTIONS:
1. Extract the exact steps mentioned in the description. Do NOT invent new steps.
2. Identify all distinct actors/systems as "swimlanes". Give each a pastel color (e.g., "#e0e7ff", "#dcfce7", "#ffedd5").
3. Chronologically model the process into the "activities" array.
4. EVERY SINGLE activity MUST have a "swimlane" field that exactly matches a name from your "swimlanes" array.

JSON SCHEMA PROTOTYPE:
{{
  "title": "<String>",
  "swimlanes": [
    {{ "name": "<Actor Name>", "color": "<Hex>" }}
  ],
  "activities": [
    {{ 
      "type": "event_or_task_or_gateway_or_parallel_gateway",
      "name": "<Step Name>",
      "swimlane": "<Exact Actor Name>"
    }}
  ]
}}

EXAMPLE INPUT:
"The user logs into the portal. If valid, the system verifies and stores it. Finally the user sees the dashboard."

EXAMPLE OUTPUT YOU MUST IMITATE:
{{
  "title": "Portal Login Process",
  "swimlanes": [
    {{ "name": "User", "color": "#e0e7ff" }},
    {{ "name": "System", "color": "#dcfce7" }}
  ],
  "activities": [
    {{ "type": "event", "event_type": "start", "name": "Start Login", "swimlane": "User" }},
    {{ "type": "task", "name": "Log into portal", "swimlane": "User" }},
    {{ 
      "type": "gateway", 
      "condition": "Is login valid?",
      "swimlane": "System",
      "yes": [
        {{ "type": "task", "name": "Verify and store", "swimlane": "System" }},
        {{ "type": "task", "name": "View dashboard", "swimlane": "User" }}
      ],
      "no": [
         {{ "type": "event", "event_type": "end", "name": "Fail Login", "swimlane": "System" }}
      ]
    }},
    {{ "type": "event", "event_type": "end", "name": "End Process", "swimlane": "User" }}
  ]
}}

CRITICAL RULES:
1. Valid types: "event", "task", "gateway", "parallel_gateway".
2. If type="event", you must include "event_type" (start/intermediate/end).
3. If type="gateway", you must include "condition" string, "yes" array, and "no" array.
4. If type="parallel_gateway", you must include "branches" array of arrays.
5. Provide ONLY the final raw JSON. Do not write markdown blocks (```json) or text before/after.
"""

    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)

    try:
        data = json.loads(json_str)
        return normalize_bpmn_analysis(data)
    except json.JSONDecodeError:
        return {
            "title": "BPMN Process",
            "swimlanes": [
                {"name": "System", "color": "#e2e8f0"}
            ],
            "activities": [
                {"type": "event", "event_type": "start", "name": "Start", "swimlane": "System"},
                {"type": "task", "name": "Default Task", "swimlane": "System"},
                {"type": "event", "event_type": "end", "name": "End Process", "swimlane": "System"}
            ]
        }
