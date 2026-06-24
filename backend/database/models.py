"""
NeuroGuard AI - Database ORM Models
====================================
SQLAlchemy models for Users, Embeddings, Events, and Model Records.
"""

import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class User(Base):
    """Registered person in the surveillance system."""
    __tablename__ = "users"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String(100), nullable=False, index=True)
    employee_id: str = Column(String(50), unique=True, nullable=False, index=True)
    department: str = Column(String(100), nullable=False)
    role: str = Column(String(50), nullable=False, default="employee")
    photo_path: Optional[str] = Column(String(500), nullable=True)
    risk_level: int = Column(Integer, nullable=False, default=0)
    watchlist_reason: Optional[str] = Column(String(255), nullable=True)
    zone_access_level: str = Column(String(50), nullable=False, default="public")
    created_at: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    # Relationships
    embeddings = relationship(
        "Embedding", back_populates="user", cascade="all, delete-orphan"
    )
    events = relationship(
        "Event", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, name='{self.name}', dept='{self.department}')>"


class Embedding(Base):
    """Face embedding vectors for a registered user."""
    __tablename__ = "embeddings"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: int = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vector = Column(Vector(512), nullable=False)  # pgvector handles numpy arrays
    is_centroid: bool = Column(Integer, default=0, nullable=False)  # SQLite bool
    created_at: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="embeddings")

    def __repr__(self) -> str:
        return f"<Embedding(id={self.id}, user_id={self.user_id}, centroid={self.is_centroid})>"


class Event(Base):
    """Recognition and stranger detection events."""
    __tablename__ = "events"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_id: Optional[int] = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: str = Column(
        String(20), nullable=False, index=True
    )  # "recognized" | "stranger"
    person_name: Optional[str] = Column(String(100), nullable=True)
    confidence: float = Column(Float, nullable=False, default=0.0)
    snn_score: Optional[float] = Column(Float, nullable=True)
    cosine_score: Optional[float] = Column(Float, nullable=True)
    cnn_latency_ms: Optional[float] = Column(Float, nullable=True)
    snn_latency_ms: Optional[float] = Column(Float, nullable=True)
    hybrid_latency_ms: Optional[float] = Column(Float, nullable=True)
    cnn_macs: Optional[int] = Column(Integer, nullable=True)
    snn_spikes_ac: Optional[int] = Column(Integer, nullable=True)
    is_identity_switch: Optional[bool] = Column(Integer, nullable=True)
    stability_score: Optional[float] = Column(Float, nullable=True)
    snapshot_path: Optional[str] = Column(String(500), nullable=True)
    threat_level: str = Column(String(20), nullable=False, default="green")
    threat_type: str = Column(String(50), nullable=False, default="none")
    threat_confidence: float = Column(Float, nullable=False, default=0.0)
    threat_persistence: int = Column(Integer, nullable=False, default=0)
    threat_score: int = Column(Integer, nullable=False, default=0)
    timestamp: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    user = relationship("User", back_populates="events")

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, type='{self.event_type}', "
            f"confidence={self.confidence:.2f})>"
        )


class ModelRecord(Base):
    """Trained SNN model metadata and checkpoints."""
    __tablename__ = "models"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    version: str = Column(String(50), nullable=False, unique=True)
    accuracy: float = Column(Float, nullable=False, default=0.0)
    num_classes: int = Column(Integer, nullable=False, default=0)
    num_epochs: int = Column(Integer, nullable=False, default=0)
    loss_final: float = Column(Float, nullable=True)
    checkpoint_path: str = Column(String(500), nullable=False)
    training_duration_seconds: float = Column(Float, nullable=True)
    is_active: bool = Column(Integer, default=0, nullable=False)  # SQLite bool
    notes: Optional[str] = Column(Text, nullable=True)
    created_at: datetime.datetime = Column(
        DateTime, default=datetime.datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<ModelRecord(id={self.id}, v='{self.version}', "
            f"acc={self.accuracy:.2f}, active={self.is_active})>"
        )
