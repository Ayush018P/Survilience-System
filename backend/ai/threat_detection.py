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
            
        # YOLO expects BGR or RGB depending on the model, Ultralytics usually handles BGR well,
        # but frame_rgb is RGB. We'll pass RGB. Ultralytics works with RGB arrays natively.
        results = self.model(frame_rgb, verbose=False, conf=0.15)
        
        threats = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                label = r.names[cls_id]
                
                if label in THREAT_CLASSES:
                    conf = float(box.conf[0].item())
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int).tolist()
                    threats.append(ThreatObject(label=label, confidence=conf, bbox=[x1, y1, x2, y2]))
                    
        return threats

class ContextFusionEngine:
    def __init__(self, persistence_threshold: int = 3):
        self.persistence_threshold = persistence_threshold
        self.consecutive_threat_frames = 0
        
    def evaluate(self, is_stranger: bool, person_name: str, threats: List[ThreatObject]) -> Tuple[str, str, float, int]:
        """
        Fuses Identity and Threat data to generate Threat Level.
        Returns: (threat_level, threat_type, max_confidence, persistence)
        """
        has_threat = len(threats) > 0
        multiple_threats = len(threats) > 1
        
        # Determine Threat Level Matrix
        if has_threat:
            self.consecutive_threat_frames += 1
            if is_stranger:
                if multiple_threats:
                    level = 'critical'
                else:
                    level = 'red'
            else:
                level = 'orange'
        else:
            # Decay persistence gradually to avoid flickering
            self.consecutive_threat_frames = max(0, self.consecutive_threat_frames - 1)
            
            if is_stranger:
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
            
        return level, threat_type, max_conf, self.consecutive_threat_frames
