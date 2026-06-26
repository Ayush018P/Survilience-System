import asyncio
import logging
import os
import cv2
import numpy as np
from pathlib import Path
from typing import List

from backend.config import settings
from backend.database.session import SessionLocal
from backend.database.models import Event

logger = logging.getLogger(__name__)

class DVRService:
    def __init__(self):
        self.dvr_dir = Path(settings.DATA_DIR) / "dvr"
        self.dvr_dir.mkdir(parents=True, exist_ok=True)
        
    def _compile_video_sync(self, event_id: int, frames: List[np.ndarray]) -> str:
        if not frames:
            return None
            
        video_filename = f"dvr_event_{event_id}.mp4"
        video_path = self.dvr_dir / video_filename
        
        # We need the dimensions from the first frame
        height, width, _ = frames[0].shape
        
        # H264 (avc1) is most compatible for web playback in standard mp4 containers
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        fps = 10.0 # Assuming ~10 frames per second
        
        out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
        
        for frame_rgb in frames:
            # OpenCV writes in BGR
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            out.write(frame_bgr)
            
        out.release()
        
        # If OpenCV failed to write, clean up
        if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
            logger.error(f"Failed to write video for event {event_id}")
            return None
            
        return str(video_path)

    async def compile_and_save_dvr(self, event_id: int, frames: List[np.ndarray]):
        """Runs in background to compile the video and update the database."""
        logger.info(f"Starting DVR compilation for event {event_id} with {len(frames)} frames...")
        try:
            video_path = await asyncio.to_thread(self._compile_video_sync, event_id, frames)
            
            if video_path:
                # Update DB
                with SessionLocal() as db:
                    event = db.query(Event).filter(Event.id == event_id).first()
                    if event:
                        event.video_path = video_path
                        db.commit()
                        logger.info(f"Saved DVR video to {video_path} for event {event_id}")
        except Exception as e:
            logger.error(f"Error compiling DVR video: {e}")

dvr_service = DVRService()
