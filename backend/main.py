import sys
import logging
from pathlib import Path

# Ensure project root is in sys.path when executed directly as a script
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import (
    HOST, PORT, DEBUG,
    FRONTEND_DIR, HINDSIGHT_URL, HINDSIGHT_API_KEY
)
from backend.models import HealthResponse
from backend.routes.customers import router as customers_router, _load_customers_file, init_customers
from backend.routes.chat import router as chat_router
from backend.routes.memory import router as memory_router
from backend.services.hindsight_service import hindsight_service
from backend.services.llm_service import llm_service

from contextlib import asynccontextmanager

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("memorydesk.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MemoryDesk AI Application...")
    init_customers()
    connected, version = hindsight_service.check_connection()
    if connected:
        logger.info(f"Hindsight Memory Server Connected! (Version: {version})")
    else:
        logger.info(f"Hindsight Server at {HINDSIGHT_URL} unreachable ({version}). Running on High-Availability Local Hindsight Persistence Bank.")
    yield
    hindsight_service.close()

app = FastAPI(
    title="MemoryDesk AI",
    description="Customer Support That Never Forgets — Powered by Hindsight Persistent Memory",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(customers_router)
app.include_router(chat_router)
app.include_router(memory_router)

@app.get("/api/health", response_model=HealthResponse, tags=["health"])
def health_check():
    """System health check and integration diagnostics."""
    connected, version = hindsight_service.check_connection()
    customers = _load_customers_file()
    return HealthResponse(
        status="operational",
        version="1.0.0",
        hindsight_connected=connected,
        hindsight_url=HINDSIGHT_URL,
        hindsight_version=version if connected else "Local Hindsight Bank Active",
        llm_provider=llm_service.provider_name,
        llm_configured=llm_service.is_configured(),
        active_customers=len(customers)
    )

# Static file serving for Frontend
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")

    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/dashboard")
    @app.get("/dashboard.html")
    def serve_dashboard():
        return FileResponse(FRONTEND_DIR / "dashboard.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
