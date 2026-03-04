"""
Diagram Generator - Orchestrates diagram generation based on type.
"""
from ..analyzers import (
    analyze_for_class_diagram,
    analyze_for_sequence_diagram,
    analyze_for_usecase_diagram,
    analyze_for_erd
)
from .class_generator import generate_class_diagram
from .sequence_generator import generate_sequence_diagram
from .usecase_generator import generate_usecase_diagram
from .erd_generator import generate_erd_diagram


async def generate_plantuml_code(description: str, diagram_type: str, include_relations: bool, analysis: dict = None) -> str:
    """Generate PlantUML code using AI analysis or provided analysis."""
    if diagram_type == "class":
        if analysis is None:
            analysis = await analyze_for_class_diagram(description)
        return generate_class_diagram(analysis, include_relations)
    elif diagram_type == "sequence":
        if analysis is None:
            analysis = await analyze_for_sequence_diagram(description)
        return generate_sequence_diagram(analysis)
    elif diagram_type == "usecase":
        if analysis is None:
            analysis = await analyze_for_usecase_diagram(description)
        return generate_usecase_diagram(analysis)
    elif diagram_type == "erd":
        if analysis is None:
            analysis = await analyze_for_erd(description)
        return generate_erd_diagram(analysis)
    else:
        if analysis is None:
            analysis = await analyze_for_class_diagram(description)
        return generate_class_diagram(analysis, include_relations)
