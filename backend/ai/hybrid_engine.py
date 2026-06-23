"""
NeuroGuard AI - Hybrid Decision Engine
=======================================
Combines SNN output probabilities with Cosine Similarity scores
to make a final recognition decision.
"""

import logging
from collections import deque
from typing import Dict, Optional, Tuple

import numpy as np
import torch

from backend.ai.snn_model import SurveillanceSNN
from backend.ai.spike_encoding import PoissonSpikeEncoder
from backend.config import settings

logger = logging.getLogger(__name__)


class DecisionResult:
    """Dataclass holding the final decision and component scores."""
    def __init__(
        self,
        person_id: Optional[int],
        person_name: str,
        confidence: float,
        is_stranger: bool,
        snn_score: float,
        cosine_score: float,
        snn_spikes_ac: int = 0,
        is_identity_switch: bool = False,
        stability_score: float = 0.0
    ):
        self.person_id = person_id
        self.person_name = person_name
        self.confidence = confidence
        self.is_stranger = is_stranger
        self.snn_score = snn_score
        self.cosine_score = cosine_score
        self.snn_spikes_ac = snn_spikes_ac
        self.is_identity_switch = is_identity_switch
        self.stability_score = stability_score


class HybridDecisionEngine:
    """
    Evaluates embeddings using both SNN and Cosine Similarity.
    Final Score = (SNN_Weight * SNN_Prob) + (Cosine_Weight * Cosine_Sim)
    """
    
    def __init__(
        self,
        snn_model: Optional[SurveillanceSNN] = None,
        idx_to_label: Optional[Dict[int, int]] = None,
        device: str = None
    ):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        self.snn_model = snn_model.to(self.device) if snn_model else None
        self.idx_to_label = idx_to_label or {}
        
        self.spike_encoder = PoissonSpikeEncoder(
            num_steps=settings.NUM_SPIKE_STEPS,
            device=self.device
        )
        
        self.snn_weight = settings.SNN_WEIGHT
        self.cosine_weight = settings.COSINE_WEIGHT
        self.threshold = settings.RECOGNITION_THRESHOLD
        
        # Scale weights to sum to 1.0 just in case
        total_weight = self.snn_weight + self.cosine_weight
        if total_weight > 0:
            self.snn_weight /= total_weight
            self.cosine_weight /= total_weight
            
        # Temporal memory
        self.history_size = 5
        self.prediction_history = deque(maxlen=self.history_size)
        self.total_detections = 0
        self.total_identity_switches = 0
        self.last_identity = None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two normalized vectors."""
        # Since they should already be L2 normalized, dot product is cosine sim
        return float(np.dot(vec1, vec2))

    def _get_best_cosine_match(
        self, embedding: np.ndarray, centroids: Dict[int, Tuple[np.ndarray, str]]
    ) -> Tuple[Optional[int], str, float]:
        """Find the centroid with highest cosine similarity."""
        if not centroids:
            return None, "Unknown", 0.0
            
        best_id = None
        best_name = "Unknown"
        best_score = -1.0
        
        for uid, (centroid_vec, name) in centroids.items():
            score = self._cosine_similarity(embedding, centroid_vec)
            if score > best_score:
                best_score = score
                best_id = uid
                best_name = name
                
        # Normalize score from [-1, 1] to [0, 1] for easier thresholding
        normalized_score = (best_score + 1.0) / 2.0
        return best_id, best_name, normalized_score

    def _get_snn_prediction(self, embedding: np.ndarray) -> Tuple[Optional[int], float, int]:
        """Get SNN class probabilities for an embedding."""
        if not self.snn_model or not self.idx_to_label:
            return None, 0.0, 0
            
        try:
            self.snn_model.eval()
            with torch.no_grad():
                # Encode to spikes: (num_steps, 512)
                spikes = self.spike_encoder.encode(embedding)
                
                # Add batch dim: (num_steps, 1, 512)
                spikes_batch = spikes.unsqueeze(1).to(self.device)
                
                # Forward pass
                spk_rec, _ = self.snn_model(spikes_batch)
                
                # Sum spikes over time: (1, num_classes)
                spike_counts = spk_rec.sum(dim=0)
                
                # Convert counts to realistic probabilities using Temperature Softmax
                # Temperature softens the 100% confidence explosion of SNN spike counts
                temperature = 2.0
                probs = torch.softmax(spike_counts.float() / temperature, dim=1).squeeze(0)
                
                # Get max probability and class index
                max_prob, max_idx = torch.max(probs, dim=0)
                
                class_idx = max_idx.item()
                prob_val = max_prob.item()
                
                # Map SNN output index back to database user_id
                user_id = self.idx_to_label.get(class_idx)
                
                return user_id, prob_val, total_spikes
                
        except Exception as e:
            logger.error(f"SNN prediction failed: {e}")
            return None, 0.0, 0

    def decide(
        self, embedding: np.ndarray, centroids: Dict[int, Tuple[np.ndarray, str]]
    ) -> DecisionResult:
        """
        Make a final recognition decision combining both models.
        """
        # 1. Cosine Similarity Match
        cos_id, cos_name, cos_score = self._get_best_cosine_match(embedding, centroids)
        
        # 2. SNN Match
        snn_id, snn_score, snn_spikes = self._get_snn_prediction(embedding)
        
        # If models disagree, we rely on Cosine for identity but SNN penalizes confidence
        # In a robust system, we check if snn_id == cos_id
        
        if snn_id is not None and cos_id is not None:
            if snn_id == cos_id:
                # Agreement: Combine scores
                final_confidence = (self.snn_weight * snn_score) + (self.cosine_weight * cos_score)
                final_id = cos_id
                final_name = cos_name
            else:
                # Disagreement: Trust Cosine more for identity, but penalize confidence
                final_confidence = cos_score * 0.7  # Penalty
                final_id = cos_id
                final_name = cos_name
        elif cos_id is not None:
            # Fallback to Cosine only (e.g. SNN not trained yet)
            final_confidence = cos_score
            final_id = cos_id
            final_name = cos_name
        else:
            # No registered users
            return DecisionResult(None, "Unknown", 0.0, True, 0.0, 0.0)
            
        # Apply Temporal Memory (Smoothing)
        self.prediction_history.append(final_id)
        if len(self.prediction_history) > 2:
            history_list = list(self.prediction_history)
            most_common_id = max(set(history_list), key=history_list.count)
            if final_id != most_common_id and history_list.count(most_common_id) >= len(history_list) // 2:
                if most_common_id is not None and most_common_id in centroids:
                    final_id = most_common_id
                    final_name = centroids[most_common_id][1]
                    
        # Calculate Stability Metrics
        self.total_detections += 1
        is_switch = False
        if self.last_identity is not None and final_id != self.last_identity:
            self.total_identity_switches += 1
            is_switch = True
            
        self.last_identity = final_id
        stability_score = 1.0 - (self.total_identity_switches / self.total_detections) if self.total_detections > 0 else 1.0
            
        # Threshold check
        is_stranger = final_confidence < self.threshold
        
        if is_stranger:
            final_id = None
            final_name = "Stranger"
            
        return DecisionResult(
            person_id=final_id,
            person_name=final_name,
            confidence=final_confidence,
            is_stranger=is_stranger,
            snn_score=snn_score,
            cosine_score=cos_score,
            snn_spikes_ac=snn_spikes,
            is_identity_switch=is_switch,
            stability_score=stability_score
        )
