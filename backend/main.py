"""
NEXUS AI PlantUML Generator v2.0

A minimal entry point that runs the modular FastAPI application.
All logic has been refactored into the app package.
"""
import uvicorn

from app import app
from app.config import HOST, PORT, MODEL_NAME


if __name__ == "__main__":
    print("=" * 60)
    print("NEXUS AI PlantUML Generator v2.0")
    print(f"Server: http://{HOST}:{PORT}")
    print(f"Using Ollama model: {MODEL_NAME}")
    print("PNG Download: Enabled")
    print("Endpoints available:")
    print("  POST /generate - Generate diagrams with PNG")
    print("  POST /generate-code - Generate code from description")
    print("  GET  /download-png/{encoded} - Download PNG")
    print("  POST /download-png-from-source - Download from source")
    print("  GET  /health - Health check")
    print("  GET  /diagram-types - Available diagram types")
    print("  GET  /languages - Supported programming languages")
    print("=" * 60)
    
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")