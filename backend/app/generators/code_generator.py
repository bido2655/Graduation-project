"""
Code Generator - Generates code in various programming languages.
"""
from typing import Optional
from ..services.llm_service import call_llm_async


async def generate_code(description: str, language: str = "python", code_type: Optional[str] = None) -> str:
    """Generate code using LLM for any programming language."""
    
    print("=" * 80)
    print(f"[CODE_GENERATOR] ENTRY POINT - Language requested: {language}")
    print(f"[CODE_GENERATOR] Description length: {len(description)}")
    print(f"[CODE_GENERATOR] Code type: {code_type}")
    print("=" * 80)
    
    language_hints = {
        "python": "Python 3 with type hints, docstrings, and best practices",
        "javascript": "JavaScript (ES6+) with modern syntax, async/await, and JSDoc comments",
        "java": "Java with proper class structure, access modifiers, and JavaDoc",
        "cpp": "C++ with modern C++17 features, proper headers, and comments",
        "sql": "SQL (PostgreSQL/MySQL/General) with CREATE TABLE, constraints, and relationships",
    }
    
    language_guide = language_hints.get(language.lower(), f"{language} with best practices")
    
    code_type_hint = f"\nCode type: {code_type}" if code_type else ""
    
    print(f"[CODE_GENERATOR] Generating code for language: {language}")
    
    # Create strong language enforcement in prompt
    language_emphasis = ""
    if language.lower() != "python":
        language_emphasis = f"\n\nIMPORTANT: You MUST generate {language} code, NOT Python. Use {language} syntax and conventions exclusively."
    
    prompt = f"""
Generate clean, runnable {language} code for this: "{description}"

LANGUAGE RULES:
- Use {language} syntax and best practices.
- Include comments and documentation ({language} style).
- If {language.lower()} is not Python, do NOT use Python syntax (no 'def', no 'class:', etc).
- Code type: {code_type or "general"}

OUTPUT:
- Generate ONLY raw {language} code.
- NO explanations, NO markdown blocks.
"""
    
    print(f"[CODE_GENERATOR] Prompt includes language: {language}")
    
    try:
        raw_code = await call_llm_async(prompt)
        
        # Validate that the generated code is in the correct language
        is_correct_language = validate_language(raw_code, language)
        
        if not is_correct_language and language.lower() != "python":
            print(f"[CODE_GENERATOR] WARNING: Generated code appears to be wrong language. Retrying with extreme emphasis...")
            
            # Try again with an even more aggressive prompt
            extreme_prompt = f"""CRITICAL INSTRUCTION: You MUST generate {language.upper()} code. DO NOT generate Python code. DO NOT use Python syntax.

I need {language.upper()} code for the following. If you generate Python, the output will be rejected.

Language Required: {language.upper()}
Syntax Required: {language.upper()}

{language.upper()} CODE ONLY. Use {language.upper()} syntax:
{"- Use #include <iostream> for headers" if language.lower() == "cpp" else ""}
{"- Use curly braces {{ }}" if language.lower() in ["cpp", "java", "javascript"] else ""}
{"- Use semicolons at end of statements" if language.lower() in ["cpp", "java", "javascript"] else ""}
{"- NO Python syntax like 'def', 'class:', or type hints" if language.lower() != "python" else ""}

Description: {description}

Generate ONLY {language.upper()} code. Start with {language.upper()} syntax immediately:
"""
            raw_code = await call_llm_async(extreme_prompt)
            print(f"[CODE_GENERATOR] Retry complete, validating again...")
            
            # Validate the retry result
            is_correct_after_retry = validate_language(raw_code, language)
            if not is_correct_after_retry:
                print(f"[CODE_GENERATOR] CRITICAL: LLM still generating wrong language after retry. Using template fallback.")
                return generate_code_fallback(description, language, code_type)
        
        # Clean markdown code blocks
        if "```" in raw_code:
            lines = raw_code.split('\n')
            code_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or not line.strip().startswith('```'):
                    code_lines.append(line)
            cleaned_code = '\n'.join(code_lines).strip()
            
            # Final validation on cleaned code
            if language.lower() != "python" and not validate_language(cleaned_code, language):
                print(f"[CODE_GENERATOR] Cleaned code still wrong language. Using fallback.")
                return generate_code_fallback(description, language, code_type)
            
            return cleaned_code
        
        return raw_code.strip()
    except Exception as e:
        print(f"Error generating code with LLM: {e}")
        return generate_code_fallback(description, language, code_type)


def validate_language(code: str, expected_language: str) -> bool:
    """Validate that generated code matches the expected language."""
    print(f"\n[VALIDATOR] Validating code for expected language: {expected_language}")
    print(f"[VALIDATOR] Code preview (first 200 chars): {code[:200]}")
    
    code_lower = code.lower()
    language_lower = expected_language.lower()
    
    # Python detection
    if language_lower != "python":
        # More specific Python indicators to avoid false positives with C++ (which has 'class', 'import' in comments, etc)
        # C++ uses 'class MyClass', Python uses 'class MyClass:'
        # C++ uses 'namespace', Python doesn't
        
        python_indicators = [
            'def ', 
            'if __name__ == "__main__":', 
            'import os', 
            'import sys', 
            'from typing',
            '    def ',
            'elif ',
            'pass\n',
            'raise Exception'
        ]
        
        # Check for these specific patterns
        if any(indicator in code_lower for indicator in python_indicators):
            print(f"[VALIDATOR] Detected Python syntax in {expected_language} code!")
            return False
            
        # secondary check: if it has 'class ' AND ':\n' but NOT ';' at end of lines, it might be python
        # But C++ also has 'class Foo {' which can be 'class Foo \n {' 
        
        # Check for python-style class definition specifically: "class Name(Base):" or "class Name:"
        # preventing match on "class Name {"
        if 'class ' in code_lower and (':\n' in code_lower or '):' in code_lower):
            # Check if it looks like C++ class
            if '{' not in code_lower and '};' not in code_lower and 'public:' not in code_lower:
                 print(f"[VALIDATOR] Detected Python class syntax in {expected_language} code!")
                 return False
    
    # C++ detection
    if language_lower == "cpp":
        cpp_indicators = ['#include', 'std::', 'cout', 'cin', 'namespace']
        if not any(indicator.lower() in code_lower for indicator in cpp_indicators):
            print(f"[VALIDATOR] Missing C++ indicators in generated code")
            # Don't fail yet, might be valid C++ without these
    
    # Java detection  
    if language_lower == "java":
        java_indicators = ['public class', 'public static', 'private ', 'protected ']
        if not any(indicator.lower() in code_lower for indicator in java_indicators):
            print(f"[VALIDATOR] Missing Java indicators in generated code")
    
    # SQL detection
    if language_lower == "sql":
        sql_indicators = ['create table', 'insert into', 'select ', 'from ', 'where ', 'join ', 'primary key', 'foreign key']
        if not any(indicator in code_lower for indicator in sql_indicators):
            print(f"[VALIDATOR] Missing SQL indicators in generated code")

    return True


def generate_code_fallback(description: str, language: str, code_type: Optional[str] = None) -> str:
    """Fallback code generation using templates."""
    
    print(f"[FALLBACK] Generating {language} code using template")
    
    if language.lower() == "python":
        return f"""# Auto-generated Python code
# Based on: {description[:100]}

def main():
    \"\"\"Main function based on description\"\"\"
    print("Code generated from: {description[:100]}")
    pass

if __name__ == "__main__":
    main()
"""
    elif language.lower() == "javascript":
        return f"""// Auto-generated JavaScript code
// Based on: {description[:100]}

function main() {{
    console.log("Code generated from: {description.replace('"', '\\"')[:100]}");
    // TODO: Implement based on description
}}

main();
"""
    elif language.lower() == "java":
        return f"""// Auto-generated Java code
// Based on: {description[:100]}

public class Main {{
    public static void main(String[] args) {{
        System.out.println("Code generated from: {description.replace('"', '\\"')[:100]}");
        // TODO: Implement based on description
    }}
}}
"""
    elif language.lower() == "cpp":
        return f"""// Auto-generated C++ code
// Based on: {description[:100]}

#include <iostream>
#include <string>

using namespace std;

int main() {{
    cout << "Code generated from: {description.replace('"', '\\"')[:100]}" << endl;
    // TODO: Implement based on description
    return 0;
}}
"""
    elif language.lower() == "sql":
        return f"""-- Auto-generated SQL code
-- Based on: {description[:100]}

-- TODO: Implement based on description
-- Example structure:
-- CREATE TABLE example (
--     id INT PRIMARY KEY,
--     name VARCHAR(255) NOT NULL
-- );
"""
    else:
        return f"""// Auto-generated {language} code
// Based on: {description[:100]}

// TODO: Implement based on description
// {description}
"""


def generate_python_code(description: str, diagram_type: str) -> str:
    """Generate Python code based on description using AI."""
    try:
        return generate_code(description, "python", diagram_type)
    except Exception as e:
        print(f"Error in LLM code generation: {e}")
        return f"""# Code for {diagram_type} diagram analysis

def process_diagram():
    \"\"\"Process the {diagram_type} diagram based on description\"\"\"
    print("Processing {diagram_type} diagram from description")
    print("Description: {description[:100]}...")

if __name__ == "__main__":
    process_diagram()
"""
