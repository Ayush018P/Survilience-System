"""
NeuroGuard AI - Health Check
=============================
Simple endpoint to verify all system components are reachable.
"""

import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import settings
from backend.database.session import get_db
from backend.schemas.schemas import HealthResponse
from backend.services.redis_service import redis_service

router = APIRouter(prefix="/api/health", tags=["System"])

# Record start time for uptime
START_TIME = time.time()


@router.get("", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """Check health of API, Database, and Redis."""
    db_status = "connected"
    redis_status = "connected" if redis_service.is_connected else "disconnected"
    
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "disconnected"
        
    overall_status = "healthy" if db_status == "connected" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        uptime_seconds=time.time() - START_TIME
    )
