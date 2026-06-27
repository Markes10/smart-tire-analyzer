"""
Federated learning trainer with Federated Averaging (FedAvg).
Simulates distributed training across vehicle nodes.
"""

import copy
import logging
import os
import time
from typing import Any, Optional

import numpy as np
import torch

from .client_simulator import FederatedClient

logger = logging.getLogger(__name__)


class FederatedTrainer:
    """
    Federated Averaging (FedAvg) trainer.
    Coordinates multiple clients and aggregates their weight updates.
    """
    
    def __init__(
        self,
        num_clients: int = 3,
        fraction: float = 1.0,
        rounds: int = 5,
        local_epochs: int = 2,
        device: str = "cpu",
    ):
        self.num_clients = num_clients
        self.fraction = fraction
        self.rounds = rounds
        self.local_epochs = local_epochs
        self.device = torch.device(device)
        self.global_model: Optional[torch.nn.Module] = None
        self.clients: list[FederatedClient] = []
        self.history: list[dict[str, Any]] = []
    
    def initialize(self, model_class=None):
        """Create global model and client simulators."""
        if model_class is None:
            from ai_model.hybrid_torch.model import HybridTireModel
            model_class = HybridTireModel
        
        self.global_model = model_class()
        self.global_model.to(self.device)
        self.global_model.train()
        
        self.clients = [
            FederatedClient(i, self.global_model, device=str(self.device))
            for i in range(self.num_clients)
        ]
        
        logger.info(
            "Federated learning initialized: %d clients, %d rounds",
            self.num_clients, self.rounds,
        )
    
    def _aggregate(self, client_updates: list[dict]) -> dict[str, np.ndarray]:
        """Federated Averaging: weight by data size."""
        total_data = sum(u["data_size"] for u in client_updates)
        if total_data == 0:
            return {}
        
        avg_update: dict[str, np.ndarray] = {}
        for name in client_updates[0]["weight_update"]:
            weighted = np.zeros_like(client_updates[0]["weight_update"][name])
            for u in client_updates:
                weighted += u["weight_update"][name] * (u["data_size"] / total_data)
            avg_update[name] = weighted
        
        return avg_update
    
    def train_round(self, round_idx: int) -> dict[str, Any]:
        """Execute one federated training round."""
        selected = np.random.choice(
            self.clients,
            size=max(1, int(self.num_clients * self.fraction)),
            replace=False,
        )
        
        client_results = []
        for client in selected:
            self._send_global_weights(client)
            result = client.train_local(epochs=self.local_epochs)
            client_results.append(result)
        
        global_update = self._aggregate(client_results)
        self._apply_global_update(global_update)
        
        round_result = {
            "round": round_idx + 1,
            "clients": len(client_results),
            "avg_loss": float(np.mean([r["loss"] for r in client_results])),
            "avg_accuracy": float(np.mean([r["accuracy"] for r in client_results])),
            "total_data_samples": sum(r["data_size"] for r in client_results),
        }
        self.history.append(round_result)
        
        logger.info(
            "Round %d/%d: loss=%.4f, acc=%.2f%%",
            round_idx + 1, self.rounds,
            round_result["avg_loss"],
            round_result["avg_accuracy"] * 100,
        )
        return round_result
    
    def train(self) -> list[dict[str, Any]]:
        """Run all federated training rounds."""
        logger.info("Starting federated training: %d rounds", self.rounds)
        start = time.time()
        
        for i in range(self.rounds):
            self.train_round(i)
        
        elapsed = time.time() - start
        logger.info("Federated training complete in %.2fs", elapsed)
        return self.history
    
    def get_status(self) -> dict[str, Any]:
        """Return current federated learning status."""
        return {
            "mode": "federated_learning_active",
            "num_clients": self.num_clients,
            "rounds_completed": len(self.history),
            "total_rounds": self.rounds,
            "fraction": self.fraction,
            "local_epochs": self.local_epochs,
            "last_round": self.history[-1] if self.history else None,
            "device": str(self.device),
        }
    
    def _send_global_weights(self, client: FederatedClient):
        weights = {
            name: param.data.cpu().numpy()
            for name, param in self.global_model.named_parameters()
        }
        client.apply_update(weights)
    
    def _apply_global_update(self, update: dict[str, np.ndarray]):
        with torch.no_grad():
            for name, param in self.global_model.named_parameters():
                if name in update:
                    param.data = torch.tensor(update[name], device=self.device)
