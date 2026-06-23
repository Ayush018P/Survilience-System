"""
NeuroGuard AI - Main FastAPI Application
=========================================
Entry point for the backend server.
Handles app lifecycle (DB, Redis), CORS, and router inclusion.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.config import settings
from backend.database.session import create_tables
from backend.services.redis_service import redis_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager.
    Runs on startup and shutdown.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Ensure required directories exist
    settings.ensure_directories()
    
    # Initialize SQLite database tables
    create_tables()
    
    # Connect to Redis
    await redis_service.connect()
    
    # Optional: Pre-load AI models here to avoid cold start on first request
    # ...
    
    yield  # App is running
    
    # Shutdown sequence
    logger.info("Shutting down NeuroGuard AI...")
    await redis_service.disconnect()


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Privacy-First Offline AI Surveillance API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routers
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    # This allows running the file directly for dev
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
