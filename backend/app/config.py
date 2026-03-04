"""
Configuration settings for the NEXUS AI PlantUML Generator.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ollama LLM Configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.2:latest")
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "-1")) # -1 for automatic allocation

# LLM Options
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.75"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "120"))

# Server Configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8002"))

# Database Configuration
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "12345")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "diagram_ai")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
