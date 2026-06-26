"""
NeuroGuard AI - Surveillance API
=================================
WebSocket endpoint for real-time video surveillance processing.
"""

import asyncio
import base64
import json
import logging
import time
from typing import Dict

import cv2
import numpy as np
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services.auth_service import get_token_remaining_ttl, decode_token
from backend.services.redis_service import redis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Surveillance"])

# Active connections for cleanup
active_connections: Dict[WebSocket, dict] = {}


async def _verify_ws_token(token: str) -> dict:
    """Verify JWT token for WebSocket connection."""
    if not token:
        raise ValueError("Missing authentication token")
    
    if redis_service.is_connected:
        if await redis_service.is_token_blacklisted(token):
            raise ValueError("Token is revoked")
            
    return decode_token(token)


@router.websocket("/surveillance")
async def surveillance_ws(websocket: WebSocket, token: str = None):
    """
    WebSocket endpoint for real-time surveillance.
    
    Flow:
    1. Client connects with JWT token
    2. Client sends base64 encoded JPEG frames
    3. Backend processes frame through AI pipeline
    4. Backend sends recognition results back
    5. Backend publishes events to Redis Pub/Sub for alerts
    """
    await websocket.accept()
    
    try:
        user = await _verify_ws_token(token)
        active_connections[websocket] = user
        logger.info(f"Surveillance WebSocket connected: {user['sub']}")
    except Exception as e:
        logger.warning(f"WebSocket auth failed: {e}")
        await websocket.send_json({"error": str(e)})
        await websocket.close(code=1008)  # Policy Violation
        return

    # In a real setup, we would instantiate the AI pipeline here.
    # Since we are building incrementally, we'll import it dynamically.
    try:
        from backend.ai.pipeline import get_pipeline
        pipeline = get_pipeline()
    except ImportError:
        logger.warning("AI Pipeline not ready yet. Running in mock mode.")
        pipeline = None

    try:
        while True:
            # 1. Receive JSON message with frame data
            data = await websocket.receive_json()
            
            if "frame" not in data:
                continue
                
            frame_id = data.get("frame_id", 0)
            base64_img = data["frame"]
            
            # Remove header if present (e.g., "data:image/jpeg;base64,...")
            if "," in base64_img:
                base64_img = base64_img.split(",")[1]
                
            # 2. Decode base64 to numpy array (in thread to avoid blocking)
            start_time = time.time()
            img_bytes = base64.b64decode(base64_img)
            enhance_low_light = data.get("enhance_low_light", False)
            
            def _decode_and_enhance(img_bytes_local, enhance):
                nparr = np.frombuffer(img_bytes_local, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is None:
                    return None
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if enhance:
                    lab = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
                    cl = clahe.apply(l)
                    limg = cv2.merge((cl, a, b))
                    frame_rgb = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
                return frame_rgb
                
            frame_rgb = await asyncio.to_thread(_decode_and_enhance, img_bytes, enhance_low_light)
            
            if frame_rgb is None:
                await websocket.send_json({"error": "Invalid frame data", "frame_id": frame_id})
                continue
            
            # 3. Process through AI Pipeline
            results = []
            threats = []
            if pipeline:
                # We will need the database session for pipeline to save events
                # For WebSockets, we manage the session manually
                from backend.database.session import SessionLocal
                with SessionLocal() as db:
                    # process_frame handles detection, SNN classification, and logging
                    pipeline_results, pipeline_threats = await pipeline.process_frame_async(frame_rgb, db)
                    results = [res.model_dump() for res in pipeline_results]
                    threats = [t.model_dump() for t in pipeline_threats]
            else:
                # Mock response for testing UI before AI is ready
                await asyncio.sleep(0.05)  # Simulate processing
            
            process_time = (time.time() - start_time) * 1000
            
            # 4. Send results back to client
            response = {
                "results": results,
                "threats": threats,
                "frame_id": frame_id,
                "processing_time_ms": round(process_time, 2),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            await websocket.send_json(response)
            
            # Update system metrics in Redis
            if redis_service.is_connected and frame_id % 10 == 0:
                import psutil
                await redis_service.update_metrics({
                    "fps": round(1000 / max(process_time, 1), 1),
                    "latency_ms": round(process_time, 2),
                    "cpu_percent": psutil.cpu_percent(),
                    "memory_percent": psutil.virtual_memory().percent
                })

    except WebSocketDisconnect:
        logger.info(f"Surveillance WebSocket disconnected: {active_connections.get(websocket, {}).get('sub')}")
        if websocket in active_connections:
            del active_connections[websocket]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            del active_connections[websocket]
