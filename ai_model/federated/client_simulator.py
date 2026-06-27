"""
Simulates a federated learning client (vehicle node).
Each client has local data and trains locally before sharing weight updates.
"""

import copy
import logging
import random
from typing import Any, Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logger = logging.getLogger(__name__)


class FederatedClient:
    """Simulates a vehicle node in federated learning."""
    
    def __init__(self, client_id: int, model: nn.Module, device: str = "cpu"):
        self.client_id = client_id
        self.device = torch.device(device)
        self.model = copy.deepcopy(model).to(self.device)
        self.local_data_size = random.randint(10, 50)
        self.accuracy = random.uniform(0.7, 0.95)
    
    def train_local(self, epochs: int = 2, lr: float = 0.001) -> dict[str, Any]:
        """Train on local synthetic data and return weight updates."""
        self.model.train()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        
        dummy_inputs = torch.randn(self.local_data_size, 3, 224, 224, device=self.device)
        dummy_targets = torch.randn(self.local_data_size, 6, device=self.device)
        
        loader = DataLoader(
            TensorDataset(dummy_inputs, dummy_targets),
            batch_size=8,
            shuffle=True,
        )
        
        total_loss = 0.0
        for epoch in range(epochs):
            epoch_loss = 0.0
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                outputs = self.model(batch_x)
                loss = nn.MSELoss()(outputs, batch_y)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            total_loss += epoch_loss / len(loader)
        
        update = {name: param.data.cpu().numpy() for name, param in self.model.named_parameters()}
        
        return {
            "client_id": self.client_id,
            "data_size": self.local_data_size,
            "loss": total_loss / epochs,
            "accuracy": self.accuracy,
            "weight_update": update,
        }
    
    def apply_update(self, global_weights: dict[str, np.ndarray]):
        """Apply aggregated global weights to local model."""
        with torch.no_grad():
            for name, param in self.model.named_parameters():
                if name in global_weights:
                    param.data = torch.tensor(global_weights[name], device=self.device)
