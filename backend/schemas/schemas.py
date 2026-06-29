"""
NeuroGuard AI - Pydantic Schemas
=================================
Request/Response models for all API endpoints.
Ensures type safety and automatic validation.
"""

import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Authentication
# =============================================================================

class LoginRequest(BaseModel):
    """Admin login request."""
    username: str = Field(..., min_length=1, max_length=50, examples=["admin"])
    password: str = Field(..., min_length=1, max_length=100, examples=["admin"])


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")
    role: str = "admin"


# =============================================================================
# Users
# =============================================================================

class UserCreate(BaseModel):
    """Request to register a new user."""
    name: str = Field(..., min_length=1, max_length=100, examples=["John Doe"])
    employee_id: str = Field(..., min_length=1, max_length=50, examples=["EMP001"])
    department: str = Field(..., min_length=1, max_length=100, examples=["Engineering"])
    role: str = Field(default="employee", max_length=50, examples=["employee"])
    risk_level: int = Field(default=0, ge=0, le=100)
    watchlist_reason: Optional[str] = Field(default=None, max_length=255)
    zone_access_level: str = Field(default="public", max_length=50)


class UserUpdate(BaseModel):
    """Request to update user fields."""
    name: Optional[str] = Field(None, max_length=100)
    department: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, max_length=50)
    risk_level: Optional[int] = Field(None, ge=0, le=100)
    watchlist_reason: Optional[str] = Field(None, max_length=255)
    zone_access_level: Optional[str] = Field(None, max_length=50)


class UserResponse(BaseModel):
    """Single user response."""
    id: int
    name: str
    employee_id: str
    department: str
    role: str
    risk_level: int
    watchlist_reason: Optional[str] = None
    zone_access_level: str
    photo_path: Optional[str] = None
    embedding_count: int = 0
    has_centroid: bool = False
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int


# =============================================================================
# Training
# =============================================================================

class TrainRequest(BaseModel):
    """Request to train/retrain the SNN model."""
    epochs: int = Field(default=100, ge=10, le=1000)
    learning_rate: float = Field(default=0.001, gt=0, lt=1)
    batch_size: int = Field(default=32, ge=8, le=256)
    notes: Optional[str] = None


class TrainResponse(BaseModel):
    """Training job response."""
    message: str
    status: str  # "queued" | "training" | "completed" | "failed"
    model_version: Optional[str] = None


class TrainingStatus(BaseModel):
    """Current training status."""
    status: str
    details: Dict = {}


# =============================================================================
# Events
# =============================================================================

class EventResponse(BaseModel):
    """Single event response."""
    id: int
    user_id: Optional[int] = None
    event_type: str
    person_name: Optional[str] = None
    confidence: float
    snn_score: Optional[float] = None
    cosine_score: Optional[float] = None
    cnn_latency_ms: Optional[float] = None
    snn_latency_ms: Optional[float] = None
    hybrid_latency_ms: Optional[float] = None
    cnn_macs: Optional[int] = None
    snn_spikes_ac: Optional[int] = None
    is_identity_switch: Optional[bool] = None
    stability_score: Optional[float] = None
    snapshot_path: Optional[str] = None
    video_path: Optional[str] = None
    threat_level: str = "green"
    threat_type: str = "none"
    threat_confidence: float = 0.0
    threat_persistence: int = 0
    threat_score: int = 0
    timestamp: datetime.datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Event list response."""
    events: List[EventResponse]
    total: int


# =============================================================================
# Analytics
# =============================================================================

class SystemMetrics(BaseModel):
    """Real-time system performance metrics."""
    fps: float = 0.0
    latency_ms: float = 0.0
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0


class AnalyticsResponse(BaseModel):
    """Full analytics response."""
    system_metrics: SystemMetrics
    total_users: int = 0
    total_events: int = 0
    total_recognized: int = 0
    total_strangers: int = 0
    recognition_accuracy: float = 0.0
    daily_counts: List[Dict] = []
    hourly_traffic: List[Dict] = []


class ThreatSummary(BaseModel):
    """Aggregation of threats by type."""
    threat_type: str
    count: int


class RecentThreatEvent(BaseModel):
    """High-risk threat event details."""
    id: int
    event_type: str
    person_name: Optional[str] = None
    threat_level: str
    threat_type: str
    threat_score: int
    threat_confidence: float
    timestamp: datetime.datetime
    snapshot_path: Optional[str] = None

    class Config:
        from_attributes = True


class ThreatAnalyticsResponse(BaseModel):
    """Advanced threat analytics dashboard data."""
    average_threat_score: float = 0.0
    high_threat_count_today: int = 0
    threats_by_type: List[ThreatSummary] = []
    threats_over_time: List[Dict] = []  # {date: str, avg_score: float, count: int}
    recent_high_threats: List[RecentThreatEvent] = []


# =============================================================================
# Surveillance (WebSocket Messages)
# =============================================================================

class BoundingBox(BaseModel):
    """Bounding box coordinates."""
    x1: int
    y1: int
    x2: int
    y2: int

class ThreatBox(BaseModel):
    """Threat bounding box."""
    label: str
    confidence: float
    bbox: BoundingBox


class RecognitionResult(BaseModel):
    """Single face recognition result."""
    event_id: Optional[int] = None
    person_id: Optional[int] = None
    person_name: str = "Unknown"
    confidence: float = 0.0
    snn_score: float = 0.0
    cosine_score: float = 0.0
    cnn_latency_ms: float = 0.0
    snn_latency_ms: float = 0.0
    hybrid_latency_ms: float = 0.0
    cnn_macs: int = 0
    snn_spikes_ac: int = 0
    is_identity_switch: bool = False
    stability_score: float = 0.0
    is_stranger: bool = True
    bbox: BoundingBox
    threat_level: str = "green"
    threat_type: str = "none"
    threat_confidence: float = 0.0
    threat_persistence: int = 0
    threat_score: int = 0


class SurveillanceResponse(BaseModel):
    """WebSocket response with all recognized faces in a frame."""
    results: List[RecognitionResult]
    threats: List[ThreatBox] = []
    frame_id: int = 0
    processing_time_ms: float = 0.0
    timestamp: str = ""


# =============================================================================
# Models
# =============================================================================

class ModelResponse(BaseModel):
    """Model record response."""
    id: int
    version: str
    accuracy: float
    num_classes: int
    num_epochs: int
    loss_final: Optional[float] = None
    training_duration_seconds: Optional[float] = None
    is_active: bool = False
    notes: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """List of model records."""
    models: List[ModelResponse]


# =============================================================================
# Settings
# =============================================================================

class SettingsUpdate(BaseModel):
    """Update system settings."""
    recognition_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    snn_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_face_size: Optional[int] = Field(None, ge=20, le=200)
    num_spike_steps: Optional[int] = Field(None, ge=10, le=200)


class SettingsResponse(BaseModel):
    """Current system settings."""
    recognition_threshold: float
    snn_weight: float
    cosine_weight: float
    min_face_size: int
    num_spike_steps: int
    face_image_size: int


# =============================================================================
# Health
# =============================================================================

class HealthResponse(BaseModel):
    """System health check response."""
    status: str = "healthy"
    version: str
    database: str = "connected"
    redis: str = "connected"
    ai_pipeline: str = "ready"
    uptime_seconds: float = 0.0


