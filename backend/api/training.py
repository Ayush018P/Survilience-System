"""
NeuroGuard AI - Training API
=============================
Trigger and monitor SNN background training via Redis queue.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import asyncio

from backend.database.session import get_db, SessionLocal
from backend.schemas.schemas import TrainingStatus, TrainRequest, TrainResponse
from backend.services.auth_service import require_admin
from backend.services.redis_service import redis_service
from backend.services.training_service import snn_trainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/train", tags=["Training"])

def run_training_task(epochs: int, lr: float, batch_size: int, notes: str):
    def run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    run_async(redis_service.set_training_status("training", {"epochs": epochs}))
    try:
        with SessionLocal() as db:
            result = snn_trainer.train_model(
                db=db,
                epochs=epochs,
                lr=lr,
                batch_size=batch_size,
                notes=notes
            )
        run_async(redis_service.set_training_status("completed", result))
        run_async(redis_service.invalidate_all_centroids())
    except Exception as e:
        logger.error(f"Training failed: {e}")
        run_async(redis_service.set_training_status("failed", {"error": str(e)}))

@router.post("", response_model=TrainResponse)
async def start_training(
    request: TrainRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    """
    Queue a new SNN training job.
    Admin only.
    """
    if not redis_service.is_connected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is not connected. Cannot queue training job.",
        )

    # Check if a training job is already running
    current_status = await redis_service.get_training_status()
    if current_status.get("status") in ["queued", "training"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A training job is already in progress.",
        )

    # Set status immediately to queued to avoid race condition
    await redis_service.set_training_status("queued", {})

    # We will execute the training job using FastAPI BackgroundTasks.
    background_tasks.add_task(
        run_training_task,
        request.epochs,
        request.learning_rate,
        request.batch_size,
        request.notes
    )

    return TrainResponse(
        message="Training job has been queued successfully.",
        status="queued"
    )


@router.get("/status", response_model=TrainingStatus)
async def get_training_status(
    admin: dict = Depends(require_admin),
):
    """Get the current SNN training status."""
    if not redis_service.is_connected:
        return TrainingStatus(status="unknown", details={"error": "Redis unavailable"})
        
    status_data = await redis_service.get_training_status()
    return TrainingStatus(
        status=status_data.get("status", "idle"),
        details=status_data.get("details", {})
    )
