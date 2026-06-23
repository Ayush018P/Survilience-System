"""
NeuroGuard AI - Spiking Neural Network (SNN) Model
===================================================
A 3-layer feed-forward SNN using Leaky Integrate-and-Fire (LIF) neurons from snntorch.
"""

import logging
from typing import Tuple

import snntorch as snn
import torch
import torch.nn as nn
from snntorch import surrogate

logger = logging.getLogger(__name__)


class SurveillanceSNN(nn.Module):
    """
    Spiking Neural Network for face recognition classification.
    
    Architecture:
    Input (512 spikes) → Linear → LIF(256) → Linear → LIF(128) → Linear → LIF(num_classes)
    """
    
    def __init__(self, num_classes: int, beta: float = 0.95):
        """
        Args:
            num_classes: Number of registered users to classify among
            beta: Default decay rate for membrane potential
        """
        super().__init__()
        
        self.num_classes = num_classes
        
        # Fast sigmoid surrogate gradient for backpropagation through discrete spikes
        spike_grad = surrogate.fast_sigmoid(slope=25)
        
        # Layer 1
        self.fc1 = nn.Linear(512, 256)
        self.lif1 = snn.Leaky(beta=beta, learn_beta=True, spike_grad=spike_grad)
        
        # Layer 2
        self.fc2 = nn.Linear(256, 128)
        self.lif2 = snn.Leaky(beta=beta, learn_beta=True, spike_grad=spike_grad)
        
        # Layer 3 (Output)
        self.fc3 = nn.Linear(128, num_classes)
        self.lif3 = snn.Leaky(beta=beta, learn_beta=True, spike_grad=spike_grad)

    def forward(self, spike_train: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass over time steps.
        
        Args:
            spike_train: Tensor of shape (num_steps, batch_size, 512)
            
        Returns:
            Tuple of (spk_rec, mem_rec):
                spk_rec: Recorded output spikes (num_steps, batch_size, num_classes)
                mem_rec: Recorded membrane potentials (num_steps, batch_size, num_classes)
        """
        # Initialize hidden states and outputs at t=0
        mem1 = self.lif1.init_leaky()
        mem2 = self.lif2.init_leaky()
        mem3 = self.lif3.init_leaky()
        
        # Lists to record outputs over time
        spk3_rec = []
        mem3_rec = []
        
        num_steps = spike_train.size(0)
        
        # Iterate over time steps
        for step in range(num_steps):
            # Input spike for current time step: (batch_size, 512)
            cur_spk = spike_train[step]
            
            # Layer 1
            cur_1 = self.fc1(cur_spk)
            spk1, mem1 = self.lif1(cur_1, mem1)
            
            # Layer 2
            cur_2 = self.fc2(spk1)
            spk2, mem2 = self.lif2(cur_2, mem2)
            
            # Layer 3 (Output)
            cur_3 = self.fc3(spk2)
            spk3, mem3 = self.lif3(cur_3, mem3)
            
            # Record output spikes and membrane potentials
            spk3_rec.append(spk3)
            mem3_rec.append(mem3)
            
        # Stack lists into tensors: (num_steps, batch_size, num_classes)
        return torch.stack(spk3_rec), torch.stack(mem3_rec)
