"""
Code Routes - Endpoints for code generation.
"""
from fastapi import APIRouter, HTTPException

from ..models import CodeRequest, CodeResponse
from ..generators import generate_code

router = APIRouter()


@router.post("/generate-code", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    """Generate code from text description using AI."""
    try:
        print(f"Generating {request.language} code for: {request.description[:100]}...")
        
        generated_code = generate_code(
            request.description,
            request.language,
            request.code_type
        )
        
        return CodeResponse(
            generated_code=generated_code,
            language=request.language
        )
        
    except Exception as e:
        print(f"Error in generate_code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating code: {str(e)}")


@router.get("/languages")
async def get_supported_languages():
    """Get supported programming languages."""
    return {
        "supported_languages": [
            "python", "javascript", "typescript", "java", "cpp", "c", "csharp",
            "go", "rust", "php", "ruby", "swift", "kotlin", "dart", "scala", "sql"
        ],
        "default": "python"
    }
