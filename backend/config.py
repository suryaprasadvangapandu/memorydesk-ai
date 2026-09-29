import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Hindsight Configuration
HINDSIGHT_URL = os.getenv("HINDSIGHT_URL", "http://localhost:8888").rstrip("/")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY", "")

# LLM Provider Configuration (Groq preferred for speed & free tier)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# Server Configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

# Directories
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
SAMPLE_CUSTOMERS_PATH = DATA_DIR / "sample_customers.json"
