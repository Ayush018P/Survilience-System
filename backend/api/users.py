"""
NeuroGuard AI - Users API
===========================
CRUD endpoints for registered users and face registration.
"""

import logging
import uuid
from pathlib import Path
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import crud
from backend.database.session import get_db
from backend.schemas.schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from backend.services.auth_service import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


def _user_to_response(user, db: Session) -> UserResponse:
    """Convert a User ORM model to a response schema."""
    embeddings = crud.get_user_embeddings(db, user.id)
    centroid = crud.get_user_centroid(db, user.id)
    return UserResponse(
        id=user.id,
        name=user.name,
        employee_id=user.employee_id,
        department=user.department,
        role=user.role,
        risk_level=user.risk_level,
        watchlist_reason=user.watchlist_reason,
        zone_access_level=user.zone_access_level,
        photo_path=user.photo_path,
        embedding_count=len(embeddings),
        has_centroid=centroid is not None,
        created_at=user.created_at,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    name: str = Form(...),
    employee_id: str = Form(...),
    department: str = Form(...),
    role: str = Form(default="employee"),
    risk_level: int = Form(default=0),
    watchlist_reason: Optional[str] = Form(default=None),
    zone_access_level: str = Form(default="public"),
    photos: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Register a new person with face photos.

    Upload 5-50 face photos. The system will:
    1. Detect faces using MTCNN
    2. Extract 512-d embeddings using InceptionResnetV1
    3. Compute a centroid embedding
    4. Store everything in the database
    5. Cache the centroid in Redis
    """
    # Check for duplicate employee ID
    existing = crud.get_user_by_employee_id(db, employee_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Employee ID '{employee_id}' is already registered",
        )

    if len(photos) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 1 photo is required",
        )

    # Save the first photo as the user's profile photo
    photo_dir = Path(settings.PHOTO_DIR) / employee_id
    photo_dir.mkdir(parents=True, exist_ok=True)

    photo_path = None
    saved_paths = []

    for i, photo in enumerate(photos):
        # Validate file type
        if photo.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            continue

        filename = f"{employee_id}_{i}_{uuid.uuid4().hex[:8]}.jpg"
        file_path = photo_dir / filename
        content = await photo.read()

        # Save the image file
        with open(file_path, "wb") as f:
            f.write(content)
        saved_paths.append(str(file_path))

        if i == 0:
            photo_path = str(file_path)

    if not saved_paths:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid image files were uploaded",
        )

    # Create the user record
    db_user = crud.create_user(
        db=db,
        name=name,
        employee_id=employee_id,
        department=department,
        role=role,
        risk_level=risk_level,
        watchlist_reason=watchlist_reason,
        zone_access_level=zone_access_level,
        photo_path=photo_path,
    )

    # Process face embeddings
    try:
        from backend.ai.pipeline import get_pipeline

        pipeline = get_pipeline()
        all_embeddings = []

        for img_path in saved_paths:
            img = Image.open(img_path).convert("RGB")
            img_np = np.array(img)
            faces = pipeline.detector.detect_and_crop(img_np)

            if faces:
                embedding = pipeline.embedder.extract(faces[0].tensor)
                all_embeddings.append(embedding)

        if all_embeddings:
            embeddings_array = np.array(all_embeddings)
            centroid = pipeline.embedder.compute_centroid(embeddings_array)

            # Store in database
            crud.store_embeddings_batch(db, db_user.id, embeddings_array, centroid)

            # Cache in Redis
            from backend.services.redis_service import redis_service

            await redis_service.cache_centroid(db_user.id, centroid, name)

            logger.info(
                f"Registered {name}: {len(all_embeddings)} embeddings extracted"
            )
        else:
            logger.warning(f"No faces detected in uploaded photos for {name}")

    except Exception as e:
        logger.error(f"Face embedding extraction failed: {e}")
        # User is still created, embeddings can be added later

    return _user_to_response(db_user, db)


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """List all registered users with optional search."""
    if search:
        users = crud.search_users(db, search)
    else:
        users = crud.get_all_users(db, skip=skip, limit=limit)

    total = crud.count_users(db)

    return UserListResponse(
        users=[_user_to_response(u, db) for u in users],
        total=total,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a specific user by ID."""
    db_user = crud.get_user(db, user_id)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return _user_to_response(db_user, db)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Update user information."""
    db_user = crud.update_user(
        db,
        user_id,
        name=update.name,
        department=update.department,
        role=update.role,
        risk_level=update.risk_level,
        watchlist_reason=update.watchlist_reason,
        zone_access_level=update.zone_access_level,
    )
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return _user_to_response(db_user, db)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete a user and all associated data (embeddings, events)."""
    # Invalidate Redis cache
    from backend.services.redis_service import redis_service

    await redis_service.invalidate_centroid(user_id)

    # Delete from database (cascading)
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    return {"message": f"User {user_id} deleted successfully"}
