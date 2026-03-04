from typing import List, Optional, Literal
from pydantic import BaseModel, Field
import uuid

class DiagramEntity(BaseModel):
    """Represents a node in the diagram (Class, Interface, etc.)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str = "class"
    attributes: List[str] = []
    methods: List[str] = []
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 150.0
    style: dict = {}

class DiagramRelationship(BaseModel):
    """Represents an edge in the diagram"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_id: str = Field(..., alias="from")
    to_id: str = Field(..., alias="to")
    type: str = "association"
    label: Optional[str] = None
    fromLabel: Optional[str] = None
    toLabel: Optional[str] = None
    
    class Config:
        populate_by_name = True

class DiagramModel(BaseModel):
    """Complete representation of a diagram"""
    entities: List[DiagramEntity] = []
    relationships: List[DiagramRelationship] = []
