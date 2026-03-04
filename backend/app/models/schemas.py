from pydantic import BaseModel, field_validator
import re
from typing import Optional, List, Dict
from datetime import datetime
from .diagram_model import DiagramModel


class DiagramRequest(BaseModel):
    """Request model for diagram generation."""
    description: str
    diagram_type: str = "class"
    include_relations: bool = True
    auto_choose: bool = False
    language: str = "python"


class RenderRequest(BaseModel):
    """Request model for rendering PlantUML code directly."""
    plantuml_code: str


class ParsePlantUMLRequest(BaseModel):
    """Request model for parsing PlantUML back into a structured model."""
    plantuml_code: str

class GenerateModelRequest(BaseModel):
    """Request model for generating a structured diagram model."""
    description: str
    diagram_type: str = "class"

class RenderModelRequest(BaseModel):
    """Request model for rendering a diagram from a structured model."""
    model: DiagramModel


class CodeRequest(BaseModel):
    """Request model for code generation."""
    description: str
    language: str = "python"
    code_type: Optional[str] = None


class EncodeRequest(BaseModel):
    """Request model for PlantUML encoding."""
    code: str


class DiagramResponse(BaseModel):
    """Response model for diagram generation."""
    diagram_source: str
    generated_code: str
    diagram_png_base64: Optional[str] = None
    encoded_plantuml: Optional[str] = None
    diagram_model: Optional[DiagramModel] = None


class CodeResponse(BaseModel):
    """Response model for code generation."""
    generated_code: str
    language: str


class DownloadRequest(BaseModel):
    """Request model for PNG download from source."""
    diagram_source: str

def check_password_strength(password: str) -> str:
    """
    Checks the strength of a password.
    Returns: 'Low', 'Medium', or 'Hard'
    """
    if len(password) < 8:
        return "Low"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))
    
    varieties = sum([has_upper, has_lower, has_digit, has_special])
    
    if len(password) >= 12 and varieties >= 3:
        return "Hard"
    if len(password) >= 8 and varieties >= 2:
        return "Medium"
    return "Low"

# --- Authentication Schemas ---

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Username must be between 3 and 20 characters.")
        if not re.match(r"^\w+$", v):
            raise ValueError("Username can only contain letters, numbers, and underscores.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        # Basic email regex
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email format.")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        strength = check_password_strength(v)
        if strength == "Low":
            raise ValueError("Password is too weak. Must be at least 8 characters and include different types of characters.")
        return v

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class VerifyPinRequest(BaseModel):
    email: str
    pin: str

class ResetPasswordRequest(BaseModel):
    email: str
    pin: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        strength = check_password_strength(v)
        if strength == "Low":
            raise ValueError("Password is too weak. Must be at least 8 characters and include different types of characters.")
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str

    class Config:
        from_attributes = True

# --- Diagram Persistence Schemas ---

class DiagramSaveRequest(BaseModel):
    user_id: int
    title: str
    description: str
    diagram_type: str
    plantuml_source: str
    generated_code: Optional[str] = None
    language: Optional[str] = "python"

class SavedDiagramResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    diagram_type: str
    plantuml_source: str
    generated_code: Optional[str] = None
    language: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True

class SimulatedEmailResponse(BaseModel):
    id: int
    recipient: str
    subject: str
    body: str
    sent_at: datetime
    is_read: bool

    class Config:
        from_attributes = True
