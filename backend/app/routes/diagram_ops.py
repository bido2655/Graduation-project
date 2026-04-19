from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.db_models import Diagram
from ..models.schemas import DiagramSaveRequest, SavedDiagramResponse
from typing import List

router = APIRouter(prefix="/diagrams", tags=["diagram-ops"])

@router.post("/save")
def save_diagram(request: DiagramSaveRequest, db: Session = Depends(get_db)):
    """
    Saves a generated diagram to the database for a specific user.
    """
    try:
        new_diagram = Diagram(
            user_id=request.user_id,
            title=request.title,
            description=request.description,
            diagram_type=request.diagram_type,
            plantuml_source=request.plantuml_source,
            generated_code=request.generated_code,
            language=request.language
        )
        db.add(new_diagram)
        db.commit()
        db.refresh(new_diagram)
        
        return {
            "message": "Diagram saved successfully",
            "diagram_id": new_diagram.id
        }
    except Exception as e:
        print(f"Error saving diagram: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save diagram to database")

@router.get("/user/{user_id}", response_model=List[SavedDiagramResponse])
def get_user_diagrams(user_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all diagrams saved by a specific user.
    """
    diagrams = db.query(Diagram).filter(Diagram.user_id == user_id).order_by(Diagram.created_at.desc()).all()
    
    result = []
    for d in diagrams:
        # Convert created_at to string and map enum to string
        result.append(SavedDiagramResponse(
            id=d.id,
            user_id=d.user_id,
            title=d.title,
            description=d.description or "",
            diagram_type=d.diagram_type,
            plantuml_source=d.plantuml_source,
            generated_code=d.generated_code,
            language=d.language,
            created_at=d.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ))
    return result
