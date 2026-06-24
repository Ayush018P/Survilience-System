"""
NeuroGuard AI - Database CRUD Operations
=========================================
Complete Create, Read, Update, Delete operations for all models.
Handles numpy array serialization for embedding vectors.
"""

import datetime
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from backend.database.models import Embedding, Event, ModelRecord, User

logger = logging.getLogger(__name__)


# =============================================================================
# Helper: Numpy <-> Bytes Serialization
# (Removed because pgvector handles numpy arrays directly)
# =============================================================================


# =============================================================================
# Users CRUD
# =============================================================================

def create_user(
    db: Session,
    name: str,
    employee_id: str,
    department: str,
    role: str = "employee",
    photo_path: Optional[str] = None,
    risk_level: int = 0,
    watchlist_reason: Optional[str] = None,
    zone_access_level: str = "public",
) -> User:
    """Create a new registered user."""
    user = User(
        name=name,
        employee_id=employee_id,
        department=department,
        role=role,
        photo_path=photo_path,
        risk_level=risk_level,
        watchlist_reason=watchlist_reason,
        zone_access_level=zone_access_level,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created user: {user.name} (ID: {user.id})")
    return user


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get a user by primary key."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_employee_id(db: Session, employee_id: str) -> Optional[User]:
    """Get a user by their employee ID."""
    return db.query(User).filter(User.employee_id == employee_id).first()


def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """List all registered users with pagination."""
    return db.query(User).order_by(desc(User.created_at)).offset(skip).limit(limit).all()


def search_users(db: Session, query: str) -> List[User]:
    """Search users by name or employee ID."""
    search_pattern = f"%{query}%"
    return (
        db.query(User)
        .filter(
            (User.name.ilike(search_pattern))
            | (User.employee_id.ilike(search_pattern))
            | (User.department.ilike(search_pattern))
        )
        .all()
    )


def update_user(
    db: Session,
    user_id: int,
    name: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    photo_path: Optional[str] = None,
    risk_level: Optional[int] = None,
    watchlist_reason: Optional[str] = None,
    zone_access_level: Optional[str] = None,
) -> Optional[User]:
    """Update user fields. Only non-None fields are updated."""
    user = get_user(db, user_id)
    if user is None:
        return None

    if name is not None:
        user.name = name
    if department is not None:
        user.department = department
    if role is not None:
        user.role = role
    if photo_path is not None:
        user.photo_path = photo_path
    if risk_level is not None:
        user.risk_level = risk_level
    if watchlist_reason is not None:
        user.watchlist_reason = watchlist_reason
    if zone_access_level is not None:
        user.zone_access_level = zone_access_level

    db.commit()
    db.refresh(user)
    logger.info(f"Updated user: {user.name} (ID: {user.id})")
    return user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete a user and all associated embeddings/events (cascading)."""
    user = get_user(db, user_id)
    if user is None:
        return False

    user_name = user.name
    db.delete(user)
    db.commit()
    logger.info(f"Deleted user: {user_name} (ID: {user_id})")
    return True


def count_users(db: Session) -> int:
    """Count total registered users."""
    return db.query(func.count(User.id)).scalar() or 0


# =============================================================================
# Embeddings CRUD
# =============================================================================

def create_embedding(
    db: Session, user_id: int, vector: np.ndarray, is_centroid: bool = False
) -> Embedding:
    """Create a new embedding vector for a user."""
    embedding = Embedding(user_id=user_id, vector=vector, is_centroid=int(is_centroid))
    db.add(embedding)
    db.commit()
    db.refresh(embedding)
    return embedding


def store_embeddings_batch(
    db: Session,
    user_id: int,
    vectors: np.ndarray,
    centroid: np.ndarray,
) -> List[Embedding]:
    """Store multiple embeddings + centroid for a user."""
    embeddings = []

    # Store individual embeddings
    for vector in vectors:
        emb = Embedding(
            user_id=user_id,
            vector=vector,
            is_centroid=0,
        )
        embeddings.append(emb)

    # Store centroid
    centroid_emb = Embedding(
        user_id=user_id,
        vector=centroid,
        is_centroid=1,
    )
    embeddings.append(centroid_emb)

    db.add_all(embeddings)
    db.commit()
    for emb in embeddings:
        db.refresh(emb)

    logger.info(
        f"Stored {len(vectors)} embeddings + centroid for user_id={user_id}"
    )
    return embeddings


def get_user_embeddings(db: Session, user_id: int) -> List[np.ndarray]:
    """Get all non-centroid embeddings for a user as numpy arrays."""
    embeddings = (
        db.query(Embedding)
        .filter(Embedding.user_id == user_id, Embedding.is_centroid == 0)
        .all()
    )
    return [np.array(emb.vector, dtype=np.float32) for emb in embeddings]


def get_user_centroid(db: Session, user_id: int) -> Optional[np.ndarray]:
    """Get the centroid embedding for a user."""
    centroid = (
        db.query(Embedding)
        .filter(Embedding.user_id == user_id, Embedding.is_centroid == 1)
        .first()
    )
    if centroid is None:
        return None
    return np.array(centroid.vector, dtype=np.float32)


def get_all_centroids(db: Session) -> Dict[int, Tuple[np.ndarray, str]]:
    """
    Get all centroid embeddings with user info.
    Returns: {user_id: (centroid_vector, user_name)}
    """
    results = (
        db.query(Embedding, User.name)
        .join(User, Embedding.user_id == User.id)
        .filter(Embedding.is_centroid == 1)
        .all()
    )
    centroids = {}
    for emb, user_name in results:
        centroids[emb.user_id] = (np.array(emb.vector, dtype=np.float32), user_name)
    return centroids


def delete_user_embeddings(db: Session, user_id: int) -> int:
    """Delete all embeddings for a user. Returns count deleted."""
    count = (
        db.query(Embedding).filter(Embedding.user_id == user_id).delete()
    )
    db.commit()
    logger.info(f"Deleted {count} embeddings for user_id={user_id}")
    return count


def get_all_embeddings_with_labels(db: Session) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Get all embeddings with their user_id labels for SNN training.
    Returns: (embeddings_array, labels_array, user_names)
    """
    results = (
        db.query(Embedding, User.name)
        .join(User, Embedding.user_id == User.id)
        .filter(Embedding.is_centroid == 0)
        .all()
    )

    if not results:
        return np.array([]), np.array([]), []

    embeddings = []
    labels = []
    user_names = {}

    for emb, user_name in results:
        embeddings.append(np.array(emb.vector, dtype=np.float32))
        labels.append(emb.user_id)
        user_names[emb.user_id] = user_name

    return (
        np.array(embeddings),
        np.array(labels),
        [user_names.get(uid, "Unknown") for uid in sorted(user_names.keys())],
    )


# =============================================================================
# Events CRUD
# =============================================================================

def create_event(
    db: Session,
    event_type: str,
    confidence: float,
    user_id: Optional[int] = None,
    person_name: Optional[str] = None,
    snn_score: Optional[float] = None,
    cosine_score: Optional[float] = None,
    cnn_latency_ms: Optional[float] = None,
    snn_latency_ms: Optional[float] = None,
    hybrid_latency_ms: Optional[float] = None,
    cnn_macs: Optional[int] = None,
    snn_spikes_ac: Optional[int] = None,
    is_identity_switch: Optional[bool] = None,
    stability_score: Optional[float] = None,
    snapshot_path: Optional[str] = None,
    threat_level: str = "green",
    threat_type: str = "none",
    threat_confidence: float = 0.0,
    threat_persistence: int = 0,
    threat_score: int = 0,
) -> Event:
    """Create a recognition/stranger event."""
    event = Event(
        user_id=user_id,
        event_type=event_type,
        person_name=person_name,
        confidence=confidence,
        snn_score=snn_score,
        cosine_score=cosine_score,
        cnn_latency_ms=cnn_latency_ms,
        snn_latency_ms=snn_latency_ms,
        hybrid_latency_ms=hybrid_latency_ms,
        cnn_macs=cnn_macs,
        snn_spikes_ac=snn_spikes_ac,
        is_identity_switch=int(is_identity_switch) if is_identity_switch is not None else None,
        stability_score=stability_score,
        snapshot_path=snapshot_path,
        threat_level=threat_level,
        threat_type=threat_type,
        threat_confidence=threat_confidence,
        threat_persistence=threat_persistence,
        threat_score=threat_score,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(
    db: Session,
    event_type: Optional[str] = None,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[Event]:
    """Query events with optional filters."""
    query = db.query(Event)

    if event_type:
        query = query.filter(Event.event_type == event_type)
    if start_date:
        query = query.filter(Event.timestamp >= start_date)
    if end_date:
        query = query.filter(Event.timestamp <= end_date)

    return query.order_by(desc(Event.timestamp)).offset(skip).limit(limit).all()


def get_today_events(db: Session) -> List[Event]:
    """Get all events from today."""
    today_start = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (
        db.query(Event)
        .filter(Event.timestamp >= today_start)
        .order_by(desc(Event.timestamp))
        .all()
    )


def count_events_by_type(
    db: Session,
    event_type: str,
    start_date: Optional[datetime.datetime] = None,
) -> int:
    """Count events of a specific type, optionally after a start date."""
    query = db.query(func.count(Event.id)).filter(Event.event_type == event_type)
    if start_date:
        query = query.filter(Event.timestamp >= start_date)
    return query.scalar() or 0


def get_daily_event_counts(
    db: Session, days: int = 7
) -> List[Dict]:
    """Get event counts grouped by day for the last N days."""
    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    events = (
        db.query(Event)
        .filter(Event.timestamp >= start_date)
        .order_by(Event.timestamp)
        .all()
    )

    daily_counts: Dict[str, Dict[str, int]] = {}
    for event in events:
        day_key = event.timestamp.strftime("%Y-%m-%d")
        if day_key not in daily_counts:
            daily_counts[day_key] = {"recognized": 0, "stranger": 0}
        daily_counts[day_key][event.event_type] = (
            daily_counts[day_key].get(event.event_type, 0) + 1
        )

    return [
        {"date": date, **counts}
        for date, counts in sorted(daily_counts.items())
    ]


def get_hourly_traffic(db: Session) -> List[Dict]:
    """Get today's event counts grouped by hour."""
    today_start = datetime.datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    events = (
        db.query(Event)
        .filter(Event.timestamp >= today_start)
        .order_by(Event.timestamp)
        .all()
    )

    hourly: Dict[int, int] = {h: 0 for h in range(24)}
    for event in events:
        hourly[event.timestamp.hour] += 1

    return [{"hour": h, "count": c} for h, c in sorted(hourly.items())]


# =============================================================================
# Model Records CRUD
# =============================================================================

def create_model_record(
    db: Session,
    version: str,
    accuracy: float,
    num_classes: int,
    num_epochs: int,
    checkpoint_path: str,
    loss_final: Optional[float] = None,
    training_duration_seconds: Optional[float] = None,
    is_active: bool = False,
    notes: Optional[str] = None,
) -> ModelRecord:
    """Record a trained model's metadata."""
    model = ModelRecord(
        version=version,
        accuracy=accuracy,
        num_classes=num_classes,
        num_epochs=num_epochs,
        checkpoint_path=checkpoint_path,
        loss_final=loss_final,
        training_duration_seconds=training_duration_seconds,
        is_active=int(is_active),
        notes=notes,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    logger.info(f"Created model record: v{version} (accuracy={accuracy:.2%})")
    return model


def get_model_record(db: Session, model_id: int) -> Optional[ModelRecord]:
    """Get a model record by ID."""
    return db.query(ModelRecord).filter(ModelRecord.id == model_id).first()


def get_active_model(db: Session) -> Optional[ModelRecord]:
    """Get the currently active model."""
    return db.query(ModelRecord).filter(ModelRecord.is_active == 1).first()


def set_active_model(db: Session, model_id: int) -> Optional[ModelRecord]:
    """Set a specific model as the active one, deactivate others."""
    # Deactivate all
    db.query(ModelRecord).update({ModelRecord.is_active: 0})
    
    # Activate target
    model = db.query(ModelRecord).filter(ModelRecord.id == model_id).first()
    if model:
        model.is_active = 1
        db.commit()
        db.refresh(model)
        logger.info(f"Activated model: v{model.version} (ID: {model.id})")
    return model


def get_all_models(db: Session) -> List[ModelRecord]:
    """List all trained models, newest first."""
    return db.query(ModelRecord).order_by(desc(ModelRecord.created_at)).all()


def delete_model_record(db: Session, model_id: int) -> bool:
    """Delete a model record."""
    model = get_model_record(db, model_id)
    if model is None:
        return False

    db.delete(model)
    db.commit()
    logger.info(f"Deleted model record: v{model.version} (ID: {model_id})")
    return True
