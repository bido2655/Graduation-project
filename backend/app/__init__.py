"""
NEXUS AI PlantUML Generator - App Package

This package contains the modular FastAPI application for generating
UML diagrams and code from natural language descriptions.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes.auth import router as auth_router
from .routes.diagrams import router as diagram_router
from .routes.diagram_ops import router as diagram_ops_router
from .routes.code import router as code_router
from .routes.download import router as download_router
from .routes.utility import router as utility_router
from .config import HOST, PORT, MODEL_NAME
from .database import engine, Base
from .models import db_models # Ensure models are loaded for table creation


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="NEXUS AI PlantUML Generator",
        description="AI-powered UML diagram and code generation from natural language",
        version="2.0.0"
    )
    
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized.")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(diagram_router)
    app.include_router(diagram_ops_router)
    app.include_router(auth_router)
    app.include_router(utility_router)
    app.include_router(code_router)
    app.include_router(download_router)
    
    return app


# Create the app instance
app = create_app()
