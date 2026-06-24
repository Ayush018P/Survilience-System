"""
NeuroGuard AI - LLM API
=======================
Endpoints for the Groq AI Assistant.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.database import crud
from backend.database.session import get_db
from backend.services.auth_service import get_current_user
from backend.services.llm_service import llm_service

router = APIRouter(prefix="/api/llm", tags=["AI Assistant"])

class ChatRequest(BaseModel):
    query: str

class ChatResponse(BaseModel):
    answer: str

class ReportResponse(BaseModel):
    report: str

@router.post("/chat", response_model=ChatResponse)
async def chat_with_assistant(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Chat with the Groq AI Assistant, providing it with recent threat context.
    """
    # Fetch recent context to inject into prompt
    recent_threats = crud.get_recent_high_threats(db, limit=20)
    threat_summary = crud.get_threat_analytics_summary(db, days=1)
    
    context = {
        "today_summary": threat_summary,
        "recent_anomalies": [
            {
                "time": t.timestamp.isoformat(),
                "type": t.threat_type,
                "score": t.threat_score,
                "person": t.person_name or "Stranger"
            } for t in recent_threats
        ]
    }
    
    answer = llm_service.query_assistant(request.query, context)
    return ChatResponse(answer=answer)


@router.post("/report", response_model=ReportResponse)
async def generate_report(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Generate an automated daily security report using Groq.
    """
    threat_summary = crud.get_threat_analytics_summary(db, days=1)
    recent_threats = crud.get_recent_high_threats(db, limit=50)
    
    context = {
        "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "metrics": threat_summary,
        "anomalies": [
            {
                "time": t.timestamp.isoformat(),
                "type": t.threat_type,
                "score": t.threat_score,
                "person": t.person_name or "Stranger"
            } for t in recent_threats
        ]
    }
    
    report = llm_service.generate_daily_summary(context)
    return ReportResponse(report=report)
