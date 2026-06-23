"""
NeuroGuard AI - Poisson Spike Encoding
======================================
Converts continuous 512-dimensional embeddings into discrete spike trains over time.
"""

import numpy as np
import torch

from backend.config import settings


class PoissonSpikeEncoder:
    """
    Encodes continuous embedding vectors into Poisson spike trains.
    Each embedding dimension [0, 1] acts as a firing rate probability.
    """
    
    def __init__(self, num_steps: int = None, device: str = None):
        self.num_steps = num_steps or settings.NUM_SPIKE_STEPS
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
    def _normalize(self, embedding: torch.Tensor) -> torch.Tensor:
        """
        Min-Max normalize the embeddings to strictly [0, 1] range.
        If batch input: Normalizes across the batch to maintain relative distances.
        """
        min_val = embedding.min(dim=-1, keepdim=True)[0]
        max_val = embedding.max(dim=-1, keepdim=True)[0]
        
        range_val = max_val - min_val
        range_val[range_val == 0] = 1.0
            
        return (embedding - min_val) / range_val
        
    def encode(self, embedding: np.ndarray) -> torch.Tensor:
        """
        Encode a single 512-d embedding into a spike train of length num_steps.
        
        Args:
            embedding: (512,) numpy array
            
        Returns:
            (num_steps, 512) binary tensor (0.0 or 1.0)
        """
        # Convert to tensor and add batch dim for generalized processing
        tensor = torch.tensor(embedding, dtype=torch.float32, device=self.device).unsqueeze(0)
        
        # Encode as batch of 1
        spike_train = self.encode_batch(tensor)
        
        # Remove batch dim: (num_steps, 1, 512) -> (num_steps, 512)
        return spike_train.squeeze(1)

    def encode_batch(self, embeddings: torch.Tensor) -> torch.Tensor:
        """
        Encode a batch of embeddings into spike trains.
        
        Args:
            embeddings: (batch_size, 512) tensor
            
        Returns:
            (num_steps, batch_size, 512) binary tensor
        """
        # 1. Normalize rates to [0, 1]
        rates = self._normalize(embeddings)
        
        # 2. Duplicate the rates across the time dimension
        # Shape: (num_steps, batch_size, 512)
        rates_expanded = rates.unsqueeze(0).repeat(self.num_steps, 1, 1)
        
        # 3. Generate random uniform noise [0, 1)
        random_noise = torch.rand_like(rates_expanded)
        
        # 4. Spike generation: Fire (1) if random noise < rate probability
        spikes = (random_noise < rates_expanded).float()
        
        return spikes
