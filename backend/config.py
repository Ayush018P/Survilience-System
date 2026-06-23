"""
NeuroGuard AI - Application Configuration
==========================================
Centralized configuration using Pydantic BaseSettings.
All values can be overridden via environment variables or .env file.
"""

import os
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # === Application ===
    APP_NAME: str = "NeuroGuard AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # === Admin Credentials (Static Login) ===
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # === JWT Configuration ===
    JWT_SECRET: str = "neuroguard-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    # === Database ===
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/neuroguard"

    # === Redis ===
    REDIS_URL: str = "redis://localhost:6379/0"

    # === AI Pipeline Configuration ===
    SNN_WEIGHT: float = 0.6
    COSINE_WEIGHT: float = 0.4
    RECOGNITION_THRESHOLD: float = 0.65
    MIN_FACE_SIZE: int = 80 # Increased from 40 to massively reduce CPU lag
    NUM_SPIKE_STEPS: int = 50
    FACE_IMAGE_SIZE: int = 160
    FACE_MARGIN: int = 20

    # === Paths ===
    SNAPSHOT_DIR: str = "./snapshots"
    MODEL_DIR: str = "./models"
    EMBEDDING_DIR: str = "./data/embeddings"
    LOG_DIR: str = "./logs"
    DATA_DIR: str = "./data"
    PHOTO_DIR: str = "./data/photos"

    # === Server ===
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    def ensure_directories(self) -> None:
        """Create all required directories if they don't exist."""
        dirs = [
            self.SNAPSHOT_DIR,
            self.MODEL_DIR,
            self.EMBEDDING_DIR,
            self.LOG_DIR,
            self.DATA_DIR,
            self.PHOTO_DIR,
        ]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
