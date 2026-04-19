from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, TIMESTAMP, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from ..database import Base
import enum
from datetime import datetime

class UserRole(enum.Enum):
    user = "user"
    admin = "admin"

class DiagramType(enum.Enum):
    class_diagram = "class"
    sequence = "sequence"
    usecase = "usecase"
    erd = "erd"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.user)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    diagrams = relationship("Diagram", back_populates="owner", cascade="all, delete-orphan")
    password_resets = relationship("PasswordReset", back_populates="user", cascade="all, delete-orphan")

class Diagram(Base):
    __tablename__ = "diagrams"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="Untitled Diagram")
    description = Column(Text)
    # Using String instead of Enum to avoid mapping issues with reserved words like 'class'
    diagram_type = Column(String(50), default="class")
    plantuml_source = Column(Text, nullable=False)
    generated_code = Column(Text)
    language = Column(String(50))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="diagrams")

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pin = Column(String(10), unique=False, index=True, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="password_resets")

class SimulatedEmail(Base):
    __tablename__ = "simulated_emails"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    is_read = Column(Boolean, default=False)
