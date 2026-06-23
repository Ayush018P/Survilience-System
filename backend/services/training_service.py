"""
NeuroGuard AI - SNN Training Service
=====================================
Handles SNN model training orchestration, including data loading, augmentation,
spike encoding, training loop, and model checkpointing.
"""

import logging
import os
import time
from typing import Dict, Tuple

import numpy as np
import torch
from snntorch import functional as SF
from sqlalchemy.orm import Session

from backend.ai.snn_model import SurveillanceSNN
from backend.ai.spike_encoding import PoissonSpikeEncoder
from backend.config import settings
from backend.database import crud

logger = logging.getLogger(__name__)


class SNNTrainer:
    """Orchestrates the training of the Spiking Neural Network."""
    
    def __init__(self, device: str = None):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        self.encoder = PoissonSpikeEncoder(
            num_steps=settings.NUM_SPIKE_STEPS,
            device=self.device
        )
        
    def _augment_embeddings(self, embeddings: np.ndarray, labels: np.ndarray, noise_factor: float = 0.05) -> Tuple[np.ndarray, np.ndarray]:
        """
        Data augmentation: Add Gaussian noise to embeddings to improve SNN robustness.
        Returns original + augmented embeddings.
        """
        if len(embeddings) == 0:
            return embeddings, labels
            
        noise = np.random.normal(loc=0.0, scale=noise_factor, size=embeddings.shape)
        augmented = embeddings + noise
        
        # L2 Normalize augmented embeddings
        norms = np.linalg.norm(augmented, axis=1, keepdims=True)
        norms[norms == 0] = 1.0 # Prevent division by zero
        augmented = augmented / norms
        
        # Concatenate original and augmented
        combined_embeddings = np.vstack([embeddings, augmented])
        combined_labels = np.concatenate([labels, labels])
        
        return combined_embeddings, combined_labels

    def train_model(self, db: Session, epochs: int = 100, lr: float = 0.001, batch_size: int = 32, notes: str = None) -> Dict:
        """
        Full training workflow.
        
        1. Fetch embeddings from DB
        2. Augment data
        3. Initialize SNN
        4. Train loop (spike encoding + CE loss)
        5. Evaluate
        6. Save checkpoint
        7. Update DB records
        """
        start_time = time.time()
        
        # 1. Fetch data
        embeddings, labels, user_names = crud.get_all_embeddings_with_labels(db)
        if len(embeddings) == 0:
            raise ValueError("No training data found. Register users first.")
            
        # Map labels to 0-indexed contiguous integers for CrossEntropyLoss
        unique_labels = sorted(list(set(labels)))
        num_classes = len(unique_labels)
        
        # If there's only 1 class, we can't really train a classifier properly, 
        # but we'll allow it for testing purposes
        if num_classes < 2:
            logger.warning(f"Only {num_classes} class(es) found. Training may not be meaningful.")
            
        label_to_idx = {lbl: i for i, lbl in enumerate(unique_labels)}
        idx_to_label = {i: lbl for lbl, i in label_to_idx.items()}
        
        y_mapped = np.array([label_to_idx[lbl] for lbl in labels])
        
        # 2. Augment data
        X_train, y_train = self._augment_embeddings(embeddings, y_mapped)
        
        # Convert to tensors
        X_tensor = torch.tensor(X_train, dtype=torch.float32)
        y_tensor = torch.tensor(y_train, dtype=torch.long)
        
        # Create DataLoader
        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # 3. Initialize model
        model = SurveillanceSNN(num_classes=num_classes).to(self.device)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        
        # Cross Entropy Loss on spike counts (SF.ce_rate_loss calculates CE on average firing rate)
        loss_fn = SF.ce_rate_loss()
        
        # 4. Training Loop
        logger.info(f"Starting SNN training on {self.device}. Epochs: {epochs}, Classes: {num_classes}")
        
        model.train()
        final_loss = 0.0
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                # Forward pass
                # a) Encode embeddings into spikes: (num_steps, batch_size, 512)
                spike_data = self.encoder.encode_batch(batch_x)
                
                # b) SNN forward
                spk_rec, _ = model(spike_data)
                
                # c) Calculate loss
                loss = loss_fn(spk_rec, batch_y)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                
            final_loss = epoch_loss / len(loader)
            
            if (epoch + 1) % 10 == 0 or epoch == epochs - 1:
                logger.debug(f"Epoch {epoch+1}/{epochs} - Loss: {final_loss:.4f}")
                
        # 5. Evaluate on training set (ideally would use validation set)
        model.eval()
        correct = 0
        total = 0
        
        with torch.no_grad():
            for batch_x, batch_y in loader:
                batch_x = batch_x.to(self.device)
                batch_y = batch_y.to(self.device)
                
                spike_data = self.encoder.encode_batch(batch_x)
                spk_rec, _ = model(spike_data)
                
                # Predict class with highest spike count
                _, predicted = spk_rec.sum(dim=0).max(1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
                
        accuracy = correct / total if total > 0 else 0.0
        logger.info(f"Training completed. Accuracy: {accuracy:.2%}, Final Loss: {final_loss:.4f}")
        
        # 6. Save checkpoint
        version = f"v{int(time.time())}"
        checkpoint_filename = f"snn_model_{version}.pt"
        checkpoint_path = os.path.join(settings.MODEL_DIR, checkpoint_filename)
        
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'num_classes': num_classes,
            'label_to_idx': label_to_idx,
            'idx_to_label': idx_to_label,
            'accuracy': accuracy,
            'version': version
        }
        
        torch.save(checkpoint, checkpoint_path)
        
        # 7. Update DB Records
        duration = time.time() - start_time
        
        model_record = crud.create_model_record(
            db=db,
            version=version,
            accuracy=accuracy,
            num_classes=num_classes,
            num_epochs=epochs,
            checkpoint_path=checkpoint_path,
            loss_final=final_loss,
            training_duration_seconds=duration,
            notes=notes
        )
        
        # Set as active
        crud.set_active_model(db, model_record.id)
        
        # Invalidate centroids cache in Redis because model changed
        # This is handled by the caller or via a background task
        
        return {
            "version": version,
            "accuracy": accuracy,
            "loss": final_loss,
            "duration_seconds": duration,
            "checkpoint_path": checkpoint_path
        }


# Global instance
snn_trainer = SNNTrainer()
