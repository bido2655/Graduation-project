"""
Class Diagram Analyzer - Analyzes descriptions for class diagrams.
"""
import json
from typing import Dict
from ..services.llm_service import call_llm_async, extract_json
from ..services.rag_service import rag_instance


def normalize_class_analysis(data: Dict) -> Dict:
    """Validate and normalize class diagram metadata with strict UML rules."""
    
    # Common attribute type mappings for auto-fix
    type_mappings = {
        "id": "int",
        "userid": "int",
        "bookid": "int",
        "cartid": "int",
        "orderid": "int",
        "paymentid": "int",
        "inventoryid": "int",
        "quantity": "int",
        "amount": "decimal",
        "price": "decimal",
        "total": "decimal",
        "name": "string",
        "title": "string",
        "author": "string",
        "email": "string",
        "password": "string",
        "description": "string",
        "paymentmethod": "string",
        "status": "string",
        "availabilitystatus": "boolean",
        "isactive": "boolean",
        "ispaid": "boolean",
        "date": "Date",
        "createdat": "Date",
        "updatedat": "Date",
        "publicationdate": "Date",
        "orderdate": "Date",
        "paymentdate": "Date",
    }
    
    # Normalize classes - ensure attributes have types
    normalized_classes = {}
    for cls in data.get("classes", []):
        cls_name = cls["name"]
        
        # Fix attributes - add types if missing
        fixed_attributes = []
        for attr in cls.get("attributes", []):
            # Handle case where LLM returns dict instead of string
            if isinstance(attr, dict):
                attr_name = attr.get("name", "unknown")
                attr_type = attr.get("type", "string")
                fixed_attributes.append(f"{attr_name}: {attr_type}")
                continue
                
            attr_clean = str(attr).strip()
            # Check if already has type (contains ":")
            if ":" not in attr_clean:
                # Try to infer type
                attr_lower = attr_clean.lower().replace("_", "").replace("-", "")
                inferred_type = type_mappings.get(attr_lower, "string")
                fixed_attributes.append(f"{attr_clean}: {inferred_type}")
            else:
                fixed_attributes.append(attr_clean)
        
        # Fix methods - ensure parentheses
        fixed_methods = []
        for method in cls.get("methods", []):
            if isinstance(method, dict):
                m_name = method.get("name", "unknown")
                m_params = method.get("parameters", "")
                m_return = method.get("returnType", "")
                method_clean = f"{m_name}({m_params})"
                if m_return:
                    method_clean += f": {m_return}"
            else:
                method_clean = str(method).strip()
                
            if not method_clean.endswith(")"):
                if "(" not in method_clean:
                    method_clean = f"{method_clean}()"
            fixed_methods.append(method_clean)
        
        normalized_classes[cls_name] = {
            "name": cls_name,
            "attributes": fixed_attributes,
            "methods": fixed_methods
        }
    
    # Invalid relationship patterns to filter/fix
    patterns_to_check = [
        ("Book", "User", "many-to-many", "remove"),
        ("Inventory", "Book", "many-to-many", "aggregation"),
        ("Book", "Inventory", "many-to-many", "flip_aggregation"),
        ("CartItem", "OrderItem", None, "remove"),
        ("OrderItem", "CartItem", None, "remove"),
        ("Cart", "Order", "one-to-many", "dependency"),
        ("Cart", "Order", "composition", "dependency"),
        ("Student", "Enrollment", "many-to-many", "one-to-many"),
        ("Enrollment", "Course", "many-to-many", "association"),
        ("Course", "CartItem", "composition", "flip_association"),
        ("Book", "CartItem", "composition", "flip_association"),
        ("Instructor", "Course", "association", "association_teaches"),
    ]
    
    # Build case-insensitive lookup for class names
    name_lookup = {name.lower(): name for name in normalized_classes.keys()}
    
    valid_relationships = []
    for rel in data.get("relationships", []):
        from_cls = rel.get("from", "")
        to_cls = rel.get("to", "")
        rel_type = rel.get("type", "association")
        
        # Try case-insensitive matching for class names
        from_cls_normalized = name_lookup.get(from_cls.lower(), from_cls)
        to_cls_normalized = name_lookup.get(to_cls.lower(), to_cls)
        
        # Skip if endpoints don't exist (even after normalization)
        if from_cls_normalized not in normalized_classes or to_cls_normalized not in normalized_classes:
            continue
        
        # Use normalized names
        from_cls = from_cls_normalized
        to_cls = to_cls_normalized
            
        # Check specific patterns
        action = None
        for p_from, p_to, p_type, p_action in patterns_to_check:
            if from_cls == p_from and to_cls == p_to:
                if p_type is None or rel_type == p_type:
                    action = p_action
                    break
        
        # Apply fixes
        if action == "remove":
            continue
            
        fixed_rel = rel.copy()
        
        if action == "flip":
            fixed_rel["from"] = to_cls
            fixed_rel["to"] = from_cls
        elif action == "flip_aggregation":
            fixed_rel["from"] = to_cls
            fixed_rel["to"] = from_cls
            fixed_rel["type"] = "aggregation"
        elif action == "flip_association":
            fixed_rel["from"] = to_cls
            fixed_rel["to"] = from_cls
            fixed_rel["type"] = "association"
            if "CartItem" in to_cls or "OrderItem" in to_cls:
                fixed_rel["label"] = "references"
        elif action == "dependency":
            fixed_rel["type"] = "dependency"
            fixed_rel["label"] = "creates"
        elif action == "aggregation":
            fixed_rel["type"] = "aggregation"
        elif action == "association":
            fixed_rel["type"] = "association"
        elif action == "one-to-many":
            fixed_rel["type"] = "one-to-many"
        elif action == "association_teaches":
            fixed_rel["type"] = "association"
            fixed_rel["label"] = "teaches"
            
        # General logic for Item <-> Product relationships
        if fixed_rel["type"] == "composition" and "CartItem" in to_cls and "Cart" not in from_cls:
            fixed_rel["from"] = to_cls
            fixed_rel["to"] = from_cls
            fixed_rel["type"] = "association"
            fixed_rel["label"] = "references"

        # FALLBACK: Generate default label if none was provided
        if not fixed_rel.get("label") or not fixed_rel["label"].strip():
            default_labels = {
                "inheritance": "extends",
                "composition": "contains",
                "aggregation": "has",
                "association": "uses",
                "dependency": "depends on",
                "one-to-many": "has many",
                "many-to-many": "relates to"
            }
            fixed_rel["label"] = default_labels.get(fixed_rel.get("type", "association"), "relates to")

        valid_relationships.append(fixed_rel)
    
    return {
        "classes": list(normalized_classes.values()),
        "relationships": valid_relationships
    }


async def analyze_for_class_diagram(description: str) -> Dict:
    """Analyze description for class diagram using AI with semantic guidance."""
    # Fetch RAG context
    context = rag_instance.get_relevant_context(description, diagram_type="class")
    
    prompt = f"""
Return valid JSON representing a class diagram for this description: "{description}"

{"REFERENCE CONTEXT (Use these examples as a syntax guide):" if context else ""}
{context if context else ""}

STRUCTURE:
{{
  "classes": [{{ "name": "Name", "attributes": ["attr: type"], "methods": ["method()"] }}],
  "relationships": [{{ "from": "Name", "to": "Target", "type": "type", "label": "verb" }}]
}}

RELATIONSHIP TYPES: association, inheritance, composition, aggregation, dependency, one-to-many, many-to-many.

STRICT RULES:
1. Direction: "from" is the OWNER/ACTOR; "to" is the OWNED/TARGET (e.g., A owns B -> A*--B).
2. attributes: ALWAYS use "name: type" format.
3. labels: EVERY relationship MUST have a verb label (e.g., "places", "contains").
4. methods: Include () parentheses.
5. Max 8 classes, each with 1-4 attributes/methods.
6. Every class must have at least one relationship.
"""
    raw_output = await call_llm_async(prompt)
    json_str = extract_json(raw_output)
    
    try:
        data = json.loads(json_str)
        return normalize_class_analysis(data)
    except json.JSONDecodeError:
        return {
            "classes": [
                {"name": "Entity", "attributes": ["id: int"], "methods": ["save()"]}
            ],
            "relationships": []
        }
