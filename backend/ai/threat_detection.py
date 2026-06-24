import logging
import time
from typing import List, Dict, Any, Tuple
import cv2
import numpy as np

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None
    logging.warning("ultralytics not installed. Threat detection will be disabled.")

logger = logging.getLogger(__name__)

# COCO dataset classes that we consider threats (Added phone/remote for easy testing)
THREAT_CLASSES = {'knife', 'scissors', 'baseball bat', 'cell phone', 'remote'}

class ThreatObject:
    def __init__(self, label: str, confidence: float, bbox: List[int]):
        self.label = label
        self.confidence = confidence
        self.bbox = bbox # [x1, y1, x2, y2]

class ThreatIntelligencePipeline:
    def __init__(self, device: str = 'cpu'):
        self.device = device
        self.model = None
        if YOLO:
            logger.info("Loading YOLOv8s for Threat Intelligence...")
            # Automatically downloads yolov8s.pt if not present
            self.model = YOLO('yolov8s.pt')
            if self.device != 'cpu':
                self.model.to(self.device)
            logger.info("YOLOv8n loaded successfully.")
            
    def detect(self, frame_rgb: np.ndarray) -> List[ThreatObject]:
        if not self.model:
            return []
        # YOLO expects BGR arrays when passing raw numpy arrays from OpenCV.
        # Since we received RGB, we must convert it back to BGR for the model to see correct colors.
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        # Lower base confidence to catch smaller/ambiguous objects like knives
        results = self.model(frame_bgr, verbose=False, conf=0.10)
        
        threats = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                label = r.names[cls_id]
                
                if label in THREAT_CLASSES:
                    conf = float(box.conf[0].item())
                    
                    # Class-specific confidence thresholds
                    # Phones/remotes are common and easily confused with hands, require 50%
                    if label in ['cell phone', 'remote'] and conf < 0.50:
                        continue
                    # Knives/scissors are critical but small/occluded, require 10%
                    if label in ['knife', 'scissors'] and conf < 0.10:
                        continue
                        
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int).tolist()
                    threats.append(ThreatObject(label=label, confidence=conf, bbox=[x1, y1, x2, y2]))
                    
        return threats

class ContextFusionEngine:
    def __init__(self, persistence_threshold: int = 3):
        self.persistence_threshold = persistence_threshold
        self.consecutive_threat_frames = 0
        
    def evaluate(self, is_stranger: bool, person_name: str, threats: List[ThreatObject], risk_level: int = 0, zone_access_level: str = "public", snn_stability_score: float = 1.0) -> Tuple[str, str, float, int, int]:
        """
        Fuses Identity, SNN metrics, and Threat data to generate a Threat Score (0-100) and Level.
        Returns: (threat_level, threat_type, max_confidence, persistence, threat_score)
        """
        has_threat = len(threats) > 0
        multiple_threats = len(threats) > 1
        
        # Base Threat Score Calculation
        threat_score = 0
        
        # 1. Identity Risk
        if is_stranger:
            threat_score += 30
        else:
            threat_score += risk_level  # Applies watchlist/risk automatically
            
        # 2. Weapon Risk & Persistence
        if has_threat:
            self.consecutive_threat_frames += 1
            # Require persistence before applying full weapon risk
            if self.consecutive_threat_frames >= self.persistence_threshold:
                threat_score += 50
                if multiple_threats:
                    threat_score += 20
        else:
            # Decay persistence gradually to avoid flickering
            self.consecutive_threat_frames = max(0, self.consecutive_threat_frames - 1)
            
        # 3. SNN Instability Risk
        # If the SNN is highly uncertain, add a penalty
        if snn_stability_score < 0.6:
            threat_score += 10
            
        # 4. Zone Risk
        if zone_access_level == "admin" and (is_stranger or risk_level > 20):
            threat_score += 40
            
        # Clamp score between 0 and 100
        threat_score = min(100, max(0, threat_score))
        
        # Determine Threat Level from Score
        if threat_score >= 80:
            level = 'critical'
        elif threat_score >= 60:
            level = 'red'
        elif threat_score >= 30:
            level = 'orange'
        elif threat_score >= 10:
            level = 'yellow'
        else:
            level = 'green'
                
        # Aggregate details
        if has_threat:
            threat_labels = list(set([t.label for t in threats]))
            threat_type = "multiple" if multiple_threats else threat_labels[0]
            max_conf = max([t.confidence for t in threats])
        else:
            threat_type = "none"
            max_conf = 0.0
            
        return level, threat_type, max_conf, self.consecutive_threat_frames, threat_score
