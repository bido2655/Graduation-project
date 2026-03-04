"""
Class Diagram Generator - Generates PlantUML class diagrams.
"""
from typing import Dict


def generate_class_diagram(data: Dict, include_relations: bool = True) -> str:
    """Generate PlantUML class diagram from AI analysis."""
    plantuml: list[str] = [
        "@startuml",
        "!theme plain",
        "skinparam class {",
        "  BackgroundColor #f0fdfa",
        "  BorderColor #2dd4bf",
        "  ArrowColor #f43f5e",
        "  FontColor #134e4a",
        "  ActorBackgroundColor #99f6e4",
        "  ActorBorderColor #0d9488",
        "}",
        "",
    ]

    for cls in data.get("classes", []):
        class_name = cls['name']
        # Quote class name if it contains non-alphanumeric characters (space, slash, etc)
        # except underscore which is usually fine, but safe to quote if not standard
        if not class_name.replace('_', '').isalnum():
            class_name = f'"{class_name}"'
        plantuml.append(f"class {class_name} {{")
        for attr in cls.get("attributes", []):
            plantuml.append(f"  - {attr}")
        for method in cls.get("methods", []):
            plantuml.append(f"  + {method}")
        plantuml.append("}")
        plantuml.append("")

    if include_relations:
        arrow_map = {
            "inheritance": "<|--",
            "composition": "*--",
            "aggregation": "o--",
            "association": "-->",
            "dependency": "..>",
            "one-to-many": '"1" --> "*"',
            "many-to-many": '"*" --> "*"'
        }
        for rel in data.get("relationships", []):
            rel_type = rel.get("type", "association")

            from_name = rel['from']
            to_name = rel['to']
            if not from_name.replace('_', '').isalnum(): from_name = f'"{from_name}"'
            if not to_name.replace('_', '').isalnum(): to_name = f'"{to_name}"'

            label = f" : {rel.get('label', '')}" if rel.get("label") else ""

            if rel_type == "one-to-many":
                plantuml.append(f'{from_name} "1" --> "*" {to_name}{label}')
            elif rel_type == "many-to-many":
                plantuml.append(f'{from_name} "*" --> "*" {to_name}{label}')
            else:
                arrow = arrow_map.get(rel_type, "-->")
                plantuml.append(f"{from_name} {arrow} {to_name}{label}")

    plantuml.append("@enduml")
    return "\n".join(plantuml)
