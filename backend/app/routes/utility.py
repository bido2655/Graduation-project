"""
Utility Routes - Root, health check, and encoding endpoints.
"""
import requests
from fastapi import APIRouter, HTTPException

from ..models import EncodeRequest, SimulatedEmailResponse
from ..services import encode_plantuml
from ..config import OLLAMA_URL, MODEL_NAME, PORT
from ..database import get_db
from ..models.db_models import SimulatedEmail
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException, Depends
from typing import List

router = APIRouter()


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "NEXUS AI PlantUML Generator v2.0",
        "status": "running",
        "endpoints": {
            "POST /generate": "Generate diagrams with AI (returns PNG base64 + encoded)",
            "POST /generate-code": "Generate code from text description",
            "GET /download-png/{encoded}": "Download diagram as PNG file",
            "POST /download-png-from-source": "Download PNG from PlantUML source",
            "POST /encode-plantuml": "Encode PlantUML for URL",
            "GET /health": "Health check",
            "GET /diagram-types": "Available diagram types",
            "GET /languages": "Supported programming languages"
        },
        "download_available": True
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        test_response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": "test", "stream": False},
            timeout=5
        )
        ollama_healthy = test_response.status_code == 200
    except:
        ollama_healthy = False
    
    return {
        "status": "healthy" if ollama_healthy else "degraded",
        "ollama_connected": ollama_healthy,
        "service": "NEXUS AI PlantUML Generator",
        "download_enabled": True
    }


@router.post("/encode-plantuml")
async def encode_plantuml_endpoint(request: EncodeRequest):
    """Encode PlantUML code and return the encoded string for URL."""
    try:
        if not request.code or not request.code.strip():
            raise HTTPException(status_code=400, detail="PlantUML code is required")
        
        encoded = encode_plantuml(request.code)
        return {
            "encoded": encoded,
            "url": f"https://www.plantuml.com/plantuml/png/{encoded}",
            "download_url": f"http://localhost:{PORT}/download-png/{encoded}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error encoding PlantUML: {str(e)}")

@router.get("/emails", response_model=List[SimulatedEmailResponse])
async def get_emails(db: Session = Depends(get_db)):
    """Fetch all simulated emails."""
    return db.query(SimulatedEmail).order_by(SimulatedEmail.sent_at.desc()).all()

@router.post("/emails/clear")
async def clear_emails(db: Session = Depends(get_db)):
    """Clear all simulated emails."""
    db.query(SimulatedEmail).delete()
    db.commit()
    return {"message": "Inbox cleared"}
