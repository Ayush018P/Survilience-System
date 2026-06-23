"""
NeuroGuard AI - Embedding Extractor
====================================
Wrapper around InceptionResnetV1 for extracting 512-d embeddings from cropped faces.
"""

import logging
from typing import List, Union

import numpy as np
import torch
from facenet_pytorch import InceptionResnetV1

logger = logging.getLogger(__name__)


class EmbeddingExtractor:
    """
    InceptionResnetV1 pretrained on VGGFace2.
    Converts 160x160 aligned face tensors into 512-dimensional embeddings.
    """
    
    def __init__(self, device: str = None):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        logger.info(f"Initializing EmbeddingExtractor (InceptionResnetV1) on {self.device}")
        
        # Load the model and set to evaluation mode
        self.model = InceptionResnetV1(pretrained='vggface2').eval().to(self.device)
        
    def extract(self, face_tensor: torch.Tensor) -> np.ndarray:
        """
        Extract a 512-d embedding for a single face tensor.
        
        Args:
            face_tensor: (3, 160, 160) tensor
            
        Returns:
            512-d normalized numpy array
        """
        with torch.no_grad():
            # Add batch dimension and move to device
            face_batch = face_tensor.unsqueeze(0).to(self.device)
            
            # Forward pass
            embedding = self.model(face_batch)
            
            # Move back to CPU and convert to numpy
            emb_np = embedding.cpu().numpy().flatten()
            
            # L2 Normalize
            norm = np.linalg.norm(emb_np)
            if norm > 0:
                emb_np = emb_np / norm
                
            return emb_np
            
    def extract_batch(self, face_tensors: Union[List[torch.Tensor], torch.Tensor]) -> np.ndarray:
        """
        Extract embeddings for a batch of face tensors (e.g., during registration).
        
        Args:
            face_tensors: List of (3, 160, 160) tensors OR (N, 3, 160, 160) tensor
            
        Returns:
            (N, 512) normalized numpy array
        """
        if isinstance(face_tensors, list):
            if not face_tensors:
                return np.array([])
            batch = torch.stack(face_tensors)
        else:
            batch = face_tensors
            
        with torch.no_grad():
            batch = batch.to(self.device)
            embeddings = self.model(batch)
            emb_np = embeddings.cpu().numpy()
            
            # L2 Normalize along the feature dimension
            norms = np.linalg.norm(emb_np, axis=1, keepdims=True)
            # Avoid division by zero
            norms[norms == 0] = 1
            emb_np = emb_np / norms
            
            return emb_np
            
    @staticmethod
    def compute_centroid(embeddings: np.ndarray) -> np.ndarray:
        """
        Compute the L2-normalized mean of multiple embeddings.
        Used to create a single robust template from multiple registration photos.
        
        Args:
            embeddings: (N, 512) numpy array
            
        Returns:
            (512,) normalized numpy array
        """
        if embeddings.ndim == 1:
            return embeddings
            
        if len(embeddings) == 0:
            raise ValueError("Cannot compute centroid of empty array")
            
        # Calculate mean across the batch
        mean_embedding = np.mean(embeddings, axis=0)
        
        # L2 Normalize
        norm = np.linalg.norm(mean_embedding)
        if norm > 0:
            mean_embedding = mean_embedding / norm
            
        return mean_embedding
