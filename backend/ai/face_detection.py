"""
NeuroGuard AI - Face Detection
===============================
Wrapper around facenet_pytorch's MTCNN for detecting and aligning faces.
"""

import logging
from typing import List

import cv2
import numpy as np
import torch
from facenet_pytorch import MTCNN

from backend.config import settings
from backend.schemas.schemas import BoundingBox

logger = logging.getLogger(__name__)


class DetectedFace:
    """Dataclass holding detection metadata and the cropped face tensor."""
    def __init__(
        self,
        tensor: torch.Tensor,
        prob: float,
        bbox: BoundingBox,
    ):
        self.tensor = tensor
        self.prob = prob
        self.bbox = bbox


class FaceDetector:
    """
    MTCNN-based multi-face detector.
    Configured for high accuracy and fast inference on CPU/GPU.
    """
    
    def __init__(self, device: str = None):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        logger.info(f"Initializing FaceDetector (MTCNN) on {self.device}")
        
        self.mtcnn = MTCNN(
            image_size=settings.FACE_IMAGE_SIZE,
            margin=settings.FACE_MARGIN,
            min_face_size=settings.MIN_FACE_SIZE,
            thresholds=[0.7, 0.8, 0.85],  # Stricter thresholds to prevent hallucinating faces on curtains/walls
            factor=0.709,
            keep_all=True,               # Keep all detected faces, not just the largest
            device=self.device
        )
        
    def detect_and_crop(self, frame: np.ndarray) -> List[DetectedFace]:
        """
        Detects faces in a frame and returns aligned, cropped tensors.
        
        Args:
            frame: RGB numpy array (H, W, C)
            
        Returns:
            List of DetectedFace objects (empty if no faces found)
        """
        detected_faces = []
        
        try:
            # MTCNN takes an RGB image array or PIL Image and returns
            # faces tensor of shape (N, 3, image_size, image_size), 
            # and probs array of shape (N,)
            boxes, probs = self.mtcnn.detect(frame)
            
            if boxes is None or probs is None:
                return []
                
            # Now we extract the aligned face tensors.
            # Using the `self.mtcnn(frame, return_prob=True)` directly gives both tensors and probs
            faces_tensors, face_probs = self.mtcnn(frame, return_prob=True)
            
            if faces_tensors is None:
                return []
                
            # If only one face, faces_tensors might not have a batch dimension 
            # depending on facenet_pytorch version. Ensure batch dimension.
            if len(faces_tensors.shape) == 3:
                faces_tensors = faces_tensors.unsqueeze(0)
                
            for i in range(len(boxes)):
                prob = face_probs[i] if face_probs is not None else probs[i]
                
                # Filter out low confidence faces
                if prob < 0.80: # Lowered from 0.90 to allow real faces on noisy webcams
                    continue
                    
                box = boxes[i]
                bbox = BoundingBox(
                    x1=int(max(0, box[0])),
                    y1=int(max(0, box[1])),
                    x2=int(min(frame.shape[1], box[2])),
                    y2=int(min(frame.shape[0], box[3]))
                )
                
                detected = DetectedFace(
                    tensor=faces_tensors[i],
                    prob=float(prob),
                    bbox=bbox
                )
                detected_faces.append(detected)
                
        except Exception as e:
            logger.error(f"Error during face detection: {e}")
            
        return detected_faces
