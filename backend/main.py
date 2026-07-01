import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.config import settings
from backend.database.session import create_tables
from backend.services.redis_service import redis_service

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Boot sequence
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    settings.ensure_directories()
    
    # SQLAlchemy create_all is fine for now, but we'll definitely need Alembic before v2 launches
    create_tables()
    
    # TODO: Redis pub/sub drops occasionally on cold starts. Need to add retry logic here - Ayush
    await redis_service.connect()
    
    yield
    
    logger.info("Graceful shutdown initiated...")
    await redis_service.disconnect()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Privacy-First Offline AI Surveillance API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

# Vercel hits us from everywhere. Leaving this open for now but we need to lock down Origins later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    # Local dev entrypoint
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
