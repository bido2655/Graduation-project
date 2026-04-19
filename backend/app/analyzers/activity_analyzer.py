"""
Activity Diagram Analyzer - Analyzes descriptions for activity diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json


def normalize_activity_analysis(data: Dict) -> Dict:
    """Validate and normalize activity diagram metadata."""
    title = data.get("title", "Activity Diagram")
    activities = data.get("activities", [])
    
    # Just ensure it's a list; recursive validation is complex and often unnecessary 
    # if the LLM follows the schema reasonably well
    if not isinstance(activities, list):
        activities = []
        
    return {
        "title": title,
        "activities": activities,
        "include_start": data.get("include_start", True),
        "include_end": data.get("include_end", True)
    }


async def analyze_for_activity_diagram(description: str) -> Dict:
    """Analyze description for activity diagram using AI."""
    prompt = f"""
You are an expert UML Activity diagram architect.
Your task is to analyze the user's process and map it into a strict JSON structure representing an Activity diagram.

USER'S PROCESS DESCRIPTION:
"{description}"

YOUR INSTRUCTIONS:
1. Extract the exact steps, tasks, and decision points mentioned in the user's description.
2. Chronologically model the process flow without inserting generic steps that were not mentioned.
3. If a flow ends inside a decision branch (e.g., "ends at Final Node"), use type "stop" or "end". If you use explicit stops inside branches, set "include_end" to false.

JSON SCHEMA PROTOTYPE:
{{
  "title": "<String>",
  "include_start": true,
  "include_end": false,
  "activities": [
     {{ "type": "action_or_condition_or_fork_or_stop_or_end", "name": "<Step Name>" }}
  ]
}}

EXAMPLE INPUT:
"First, enter credentials. If valid, grant access and stop at Success. If invalid, show error and stop at Failure."

EXAMPLE OUTPUT YOU MUST IMITATE:
{{
  "title": "Login Process",
  "include_start": true,
  "include_end": false,
  "activities": [
    {{ "type": "action", "name": "Enter credentials" }},
    {{ 
      "type": "condition", 
      "condition": "Are credentials valid?", 
      "yes": [
        {{ "type": "action", "name": "Grant Access" }},
        {{ "type": "stop", "name": "Success" }}
      ],
      "no": [
        {{ "type": "action", "name": "Show error" }},
        {{ "type": "stop", "name": "Failure" }}
      ]
    }}
  ]
}}

CRITICAL RULES:
1. Valid types: "action", "condition", "fork", "stop", "end", "start".
2. If type="condition", you must include "condition" string, "yes" array, and optionally "no" array. If a branch ends the flow entirely, add a "stop" or "end" step at the end of that array.
3. If type="fork" (for parallel tasks), you must include "branches" array of arrays.
4. "include_end" should be false if you place "stop" elements inside branches, otherwise they will merge back together.
5. Provide ONLY the final raw JSON. Do not write markdown blocks (```json) or text before/after.
"""

    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)

    try:
        data = json.loads(json_str)
        return normalize_activity_analysis(data)
    except json.JSONDecodeError:
        return {
            "title": "Activity Diagram",
            "activities": [
                {"type": "action", "name": "Initialize"},
                {"type": "action", "name": "Process Default Flow"},
                {"type": "action", "name": "Finish"}
            ]
        }
