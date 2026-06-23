"""
NeuroGuard AI - API Router
==========================
Aggregates all API endpoints into a single router.
"""

from fastapi import APIRouter

from backend.api import auth, users, training, surveillance, events, analytics, health

api_router = APIRouter()

# Include all module routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(training.router)
api_router.include_router(surveillance.router)  # includes /ws/surveillance
api_router.include_router(events.router)        # includes /api/events and /api/events/ws
api_router.include_router(analytics.router)
api_router.include_router(health.router)
