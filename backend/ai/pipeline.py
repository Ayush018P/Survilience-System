"""
NeuroGuard AI - Full AI Pipeline Orchestrator
==============================================
Singleton class that manages the complete flow:
Webcam Frame -> MTCNN -> ResNet -> Spike -> SNN -> Hybrid -> Result
"""

import asyncio
import logging
import os
import uuid
import time
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from sqlalchemy.orm import Session

from backend.ai.embeddings import EmbeddingExtractor
from backend.ai.face_detection import FaceDetector
from backend.ai.hybrid_engine import DecisionResult, HybridDecisionEngine
from backend.ai.snn_model import SurveillanceSNN
from backend.ai.motion_detector import MotionDetector
from backend.ai.threat_detection import ThreatIntelligencePipeline, ContextFusionEngine
from backend.config import settings
from backend.database import crud
from backend.schemas.schemas import RecognitionResult, BoundingBox, ThreatBox
from backend.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class AIPipeline:
    """Orchestrates detection, embedding, and classification."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AIPipeline, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        # Prevent re-initialization if already initialized
        if hasattr(self, 'initialized') and self.initialized:
            return
            
        logger.info("Initializing Full AI Pipeline...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        self.detector = FaceDetector(device=self.device)
        self.embedder = EmbeddingExtractor(device=self.device)
        self.motion_detector = MotionDetector(threshold=25, min_area=500)
        
        # Context-Aware Threat Intelligence
        self.threat_pipeline = ThreatIntelligencePipeline(device=self.device)
        self.fusion_engine = ContextFusionEngine(persistence_threshold=3)
        
        self.engine = None
        
        self.initialized = True
        
    def load_active_model(self, db: Session) -> bool:
        """Load the active SNN model from DB/disk."""
        try:
            active_record = crud.get_active_model(db)
            if not active_record or not os.path.exists(active_record.checkpoint_path):
                logger.warning("No active SNN model found. Pipeline will fallback to Cosine Similarity only.")
                self.engine = HybridDecisionEngine(device=self.device)
                return False
                
            checkpoint = torch.load(active_record.checkpoint_path, map_location=self.device)
            num_classes = checkpoint.get('num_classes', active_record.num_classes)
            idx_to_label = checkpoint.get('idx_to_label', {})
            
            snn_model = SurveillanceSNN(num_classes=num_classes)
            snn_model.load_state_dict(checkpoint['model_state_dict'])
            snn_model.eval()
            
            self.engine = HybridDecisionEngine(
                snn_model=snn_model,
                idx_to_label=idx_to_label,
                device=self.device
            )
            logger.info(f"Loaded active SNN model: {active_record.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load SNN model: {e}")
            self.engine = HybridDecisionEngine(device=self.device)
            return False

    async def _get_centroids(self, db: Session) -> Dict[int, Tuple[np.ndarray, str]]:
        """Fetch centroids from Redis cache, fallback to SQLite."""
        if redis_service.is_connected:
            cached = await redis_service.get_all_cached_centroids()
            if cached:
                return cached
                
        # Fallback to DB
        logger.debug("Centroids cache miss, loading from DB")
        centroids = crud.get_all_centroids(db)
        
        # Repopulate cache
        if redis_service.is_connected:
            for uid, (vec, name) in centroids.items():
                await redis_service.cache_centroid(uid, vec, name)
                
        return centroids

    async def process_frame_async(self, frame_rgb: np.ndarray, db: Session) -> List[RecognitionResult]:
        """
        Process a single frame from the webcam.
        
        1. Detect faces
        2. Extract embeddings
        3. Run hybrid decision engine
        4. Detect Threats (YOLO)
        5. Context Fusion (Identity + Threat)
        6. Log events (strangers/recognition)
        7. Return results
        """
        # Ensure engine is loaded
        if self.engine is None:
            self.load_active_model(db)
            
        results = []
        threats_response = []
        
        # 0. Motion Detection
        if not self.motion_detector.detect(frame_rgb):
            return results, threats_response
            
        hybrid_start_time = time.perf_counter()
        
        # 4. Threat Detection (Run globally on frame)
        detected_threats = self.threat_pipeline.detect(frame_rgb)
        for t in detected_threats:
            threats_response.append(ThreatBox(label=t.label, confidence=t.confidence, bbox=BoundingBox(x1=t.bbox[0], y1=t.bbox[1], x2=t.bbox[2], y2=t.bbox[3])))
            
        # 1. Detect
        detected_faces = self.detector.detect_and_crop(frame_rgb)
        if not detected_faces:
            # Even if no faces, we should return if there are threats? Wait, MVP: return faces + threats.
            return results, threats_response
            
        # 2. Get centroids
        centroids = await self._get_centroids(db)
        
        for face in detected_faces:
            # 3. Extract Embedding
            cnn_start_time = time.perf_counter()
            embedding = self.embedder.extract(face.tensor)
            cnn_latency_ms = (time.perf_counter() - cnn_start_time) * 1000.0
            cnn_macs = 2800000000  # Estimate for InceptionResnetV1
            
            # 4. Decide
            snn_start_time = time.perf_counter()
            decision: DecisionResult = self.engine.decide(embedding, centroids)
            snn_latency_ms = (time.perf_counter() - snn_start_time) * 1000.0
            
            hybrid_latency_ms = (time.perf_counter() - hybrid_start_time) * 1000.0
            
            # Create response schema
            result = RecognitionResult(
                person_id=decision.person_id,
                person_name=decision.person_name,
                confidence=decision.confidence,
                snn_score=decision.snn_score,
                cosine_score=decision.cosine_score,
                cnn_latency_ms=cnn_latency_ms,
                snn_latency_ms=snn_latency_ms,
                hybrid_latency_ms=hybrid_latency_ms,
                cnn_macs=cnn_macs,
                snn_spikes_ac=decision.snn_spikes_ac,
                is_identity_switch=decision.is_identity_switch,
                stability_score=decision.stability_score,
                is_stranger=decision.is_stranger,
                bbox=face.bbox
            )
            
            # 5. Context Fusion
            level, t_type, t_conf, t_pers = self.fusion_engine.evaluate(
                is_stranger=decision.is_stranger,
                person_name=decision.person_name,
                threats=detected_threats
            )
            result.threat_level = level
            result.threat_type = t_type
            result.threat_confidence = t_conf
            result.threat_persistence = t_pers
            
            results.append(result)
            
            # 6. Log Events asynchronously
            await self._log_event(frame_rgb, result, face.bbox, db)
            
        return results, threats_response
        
    async def _log_event(self, frame: np.ndarray, result: RecognitionResult, bbox: BoundingBox, db: Session):
        """Save event to DB and publish to Redis."""
        event_type = "stranger" if result.is_stranger else "recognized"
        
        # Check if we should log (don't log the same person 30 times a second)
        # In a real system we'd use Redis to debounce events (e.g. only log once every 5 seconds per person)
        
        # Save snapshot if stranger
        snapshot_path = None
        if result.is_stranger:
            filename = f"stranger_{uuid.uuid4().hex[:8]}.jpg"
            snapshot_path = os.path.join(settings.SNAPSHOT_DIR, filename)
            
            # Crop the face for the snapshot (with some padding)
            pad = 20
            h, w, _ = frame.shape
            x1 = max(0, bbox.x1 - pad)
            y1 = max(0, bbox.y1 - pad)
            x2 = min(w, bbox.x2 + pad)
            y2 = min(h, bbox.y2 + pad)
            
            face_crop = frame[y1:y2, x1:x2]
            
            # Convert back to BGR for saving
            face_bgr = cv2.cvtColor(face_crop, cv2.COLOR_RGB2BGR)
            cv2.imwrite(snapshot_path, face_bgr)
            
        # Create DB record
        try:
            event_record = crud.create_event(
                db=db,
                event_type=event_type,
                confidence=result.confidence,
                user_id=result.person_id,
                person_name=result.person_name,
                snn_score=result.snn_score,
                cosine_score=result.cosine_score,
                cnn_latency_ms=result.cnn_latency_ms,
                snn_latency_ms=result.snn_latency_ms,
                hybrid_latency_ms=result.hybrid_latency_ms,
                cnn_macs=result.cnn_macs,
                snn_spikes_ac=result.snn_spikes_ac,
                is_identity_switch=result.is_identity_switch,
                stability_score=result.stability_score,
                snapshot_path=snapshot_path,
                threat_level=result.threat_level,
                threat_type=result.threat_type,
                threat_confidence=result.threat_confidence,
                threat_persistence=result.threat_persistence
            )
            
            # Publish to Redis Pub/Sub for live dashboard alerts
            if redis_service.is_connected:
                from backend.schemas.schemas import EventResponse
                event_schema = EventResponse.model_validate(event_record)
                
                # Fix datetime serialization for JSON
                event_dict = event_schema.model_dump()
                event_dict['timestamp'] = event_dict['timestamp'].isoformat()
                
                await redis_service.publish_event(event_dict)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Failed to log event: {e}")


# Singleton getter
def get_pipeline() -> AIPipeline:
    return AIPipeline()
