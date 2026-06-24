"""
NeuroGuard AI - Events API
===========================
REST endpoints for event queries and exports, plus WebSocket for live alerts.
"""

import csv
import io
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import crud
from backend.database.session import get_db
from backend.schemas.schemas import EventListResponse, EventResponse
from backend.services.auth_service import get_current_user
from backend.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["Events"])


@router.get("", response_model=EventListResponse)
async def list_events(
    event_type: Optional[str] = Query(None, description="recognized or stranger"),
    days: int = Query(7, description="Number of days to look back"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List surveillance events with optional filtering."""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    events = crud.get_events(
        db, 
        event_type=event_type, 
        start_date=start_date, 
        skip=skip, 
        limit=limit
    )
    
    # We count manually here for simplicity, in production you'd use a real count query
    total = crud.count_events_by_type(db, event_type, start_date) if event_type else crud.count_events_by_type(db, "recognized", start_date) + crud.count_events_by_type(db, "stranger", start_date)

    return EventListResponse(
        events=[EventResponse.model_validate(e) for e in events],
        total=total
    )


@router.get("/export")
async def export_events_csv(
    days: int = Query(30, description="Number of days to export"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Export events as a CSV file."""
    start_date = datetime.utcnow() - timedelta(days=days)
    events = crud.get_events(db, start_date=start_date, limit=10000)
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Timestamp", "Type", "Person Name", "Confidence", 
        "SNN Score", "Cosine Score", "Snapshot Path"
    ])
    
    # Data rows
    for e in events:
        writer.writerow([
            e.id,
            e.timestamp.isoformat(),
            e.event_type,
            e.person_name or "N/A",
            f"{e.confidence:.4f}",
            f"{e.snn_score:.4f}" if e.snn_score else "N/A",
            f"{e.cosine_score:.4f}" if e.cosine_score else "N/A",
            e.snapshot_path or ""
        ])
        
    output.seek(0)
    
    # Return as downloadable file
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"neuroguard_events_{timestamp_str}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{event_id}/report")
async def download_incident_report(
    event_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Generate and download a PDF Incident Report."""
    from backend.services.reporting_service import reporting_service
    from fastapi.responses import FileResponse
    from fastapi import HTTPException, status
    
    event = crud.get_events(db, skip=0, limit=1) # Need to get by ID
    # crud.py doesn't have get_event by id, let's just query it
    event = db.query(crud.Event).filter(crud.Event.id == event_id).first()
    
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
        
    try:
        pdf_path = reporting_service.generate_incident_report(event)
        filename = pdf_path.split("/")[-1] if "/" in pdf_path else pdf_path.split("\\")[-1]
        
        return FileResponse(
            path=pdf_path,
            filename=filename,
            media_type="application/pdf"
        )
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate incident report PDF."
        )

# =============================================================================
# Live Events WebSocket (Pub/Sub)
# =============================================================================

@router.websocket("/ws")
async def live_events_ws(websocket: WebSocket, token: str = None):
    """
    Subscribe to real-time events via Redis Pub/Sub.
    Used by the Alerts dashboard to show notifications instantly.
    """
    await websocket.accept()
    
    try:
        # We need the inner verify token logic without dependency injection
        from backend.api.surveillance import _verify_ws_token
        user = await _verify_ws_token(token)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close(code=1008)
        return

    if not redis_service.is_connected:
        await websocket.send_json({"error": "Redis unavailable. Real-time events disabled."})
        # Keep connection open but it won't receive events
        while True:
            try:
                await websocket.receive_text() # keep-alive loop
            except WebSocketDisconnect:
                break
        return

    try:
        # Create a task to listen to Redis and forward to WebSocket
        async for event_data in redis_service.subscribe_events():
            await websocket.send_json(event_data)
            
    except WebSocketDisconnect:
        logger.info(f"Live events WebSocket disconnected for {user['sub']}")
    except Exception as e:
        logger.error(f"Live events WebSocket error: {e}")
