"""
NeuroGuard AI - Analytics API
==============================
System performance and recognition statistics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.session import get_db
from backend.schemas.schemas import AnalyticsResponse, SystemMetrics, ThreatAnalyticsResponse
from backend.services.auth_service import get_current_user
from backend.services.redis_service import redis_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Get system-wide analytics for the dashboard.
    Combines live metrics from Redis with historical data from SQLite.
    """
    # 1. Live system metrics from Redis (FPS, CPU, etc.)
    sys_metrics = SystemMetrics()
    if redis_service.is_connected:
        cached_metrics = await redis_service.get_metrics()
        if cached_metrics:
            sys_metrics = SystemMetrics(**cached_metrics)

    # 2. Database aggregates
    total_users = crud.count_users(db)
    
    # Events today
    today_recognized = crud.count_events_by_type(db, "recognized", start_date=None) # We need to update count query
    # Simple hack: just fetch today's events and count
    today_events = crud.get_today_events(db)
    recognized = sum(1 for e in today_events if e.event_type == "recognized")
    strangers = sum(1 for e in today_events if e.event_type == "stranger")
    
    total_events_today = recognized + strangers
    
    # 3. Accuracy Calculation (from latest active model)
    active_model = crud.get_active_model(db)
    accuracy = active_model.accuracy * 100 if active_model else 0.0

    # 4. Chart Data
    daily_counts = crud.get_daily_event_counts(db, days=7)
    hourly_traffic = crud.get_hourly_traffic(db)

    return AnalyticsResponse(
        system_metrics=sys_metrics,
        total_users=total_users,
        total_events=total_events_today,
        today_recognized=recognized,
        today_strangers=strangers,
        recognition_accuracy=accuracy,
        daily_counts=daily_counts,
        hourly_traffic=hourly_traffic,
    )


@router.get("/threats", response_model=ThreatAnalyticsResponse)
async def get_threat_analytics(
    days: int = 7,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Get advanced threat intelligence metrics.
    """
    summary = crud.get_threat_analytics_summary(db, days=days)
    recent = crud.get_recent_high_threats(db, limit=10)
    
    return ThreatAnalyticsResponse(
        average_threat_score=summary["average_threat_score"],
        high_threat_count_today=summary["high_threat_count_today"],
        threats_by_type=summary["threats_by_type"],
        threats_over_time=summary["threats_over_time"],
        recent_high_threats=recent,
    )
