"""
Simplified GAN-based synthetic tire image generator.
Generates realistic tire wear pattern images for rare wear classes.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn

logger = logging.getLogger(__name__)


class TireGANGenerator(nn.Module):
    """
    Generator network for synthetic tire images.
    Takes random noise + wear pattern label -> 224x224 tire image.
    """
    
    def __init__(self, latent_dim: int = 100, num_classes: int = 6):
        super().__init__()
        self.latent_dim = latent_dim
        self.num_classes = num_classes
        
        self.label_embed = nn.Embedding(num_classes, latent_dim)
        
        self.model = nn.Sequential(
            nn.Linear(latent_dim * 2, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Linear(512, 1024),
            nn.BatchNorm1d(1024),
            nn.ReLU(),
            nn.Linear(1024, 2048),
            nn.BatchNorm1d(2048),
            nn.ReLU(),
            nn.Linear(2048, 4096),
            nn.BatchNorm1d(4096),
            nn.ReLU(),
            nn.Linear(4096, 3 * 224 * 224),
            nn.Tanh(),
        )
    
    def forward(self, noise: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        label_emb = self.label_embed(labels)
        combined = torch.cat([noise, label_emb], dim=1)
        img = self.model(combined)
        return img.view(-1, 3, 224, 224)


class TireGANDiscriminator(nn.Module):
    """Conditional discriminator for tire image GAN."""
    
    def __init__(self, num_classes: int = 6):
        super().__init__()
        self.label_embed = nn.Embedding(num_classes, 3 * 224 * 224)
        
        self.model = nn.Sequential(
            nn.Linear(2 * 3 * 224 * 224, 1024),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(1024, 512),
            nn.LeakyReLU(0.2),
            nn.Dropout(0.3),
            nn.Linear(512, 256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 1),
            nn.Sigmoid(),
        )
    
    def forward(self, images: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        label_emb = self.label_embed(labels)
        img_flat = images.view(images.size(0), -1)
        combined = torch.cat([img_flat, label_emb], dim=1)
        return self.model(combined)


def generate_synthetic_tire_dataset(
    generator: TireGANGenerator,
    num_images: int = 100,
    target_classes: Optional[list[int]] = None,
    device: str = "cpu",
) -> np.ndarray:
    """Generate a batch of synthetic tire images."""
    generator.eval()
    generator.to(device)
    
    if target_classes is None:
        target_classes = list(range(generator.num_classes))
    
    all_images = []
    with torch.no_grad():
        for cls in target_classes:
            noise = torch.randn(num_images // len(target_classes), generator.latent_dim, device=device)
            labels = torch.full((num_images // len(target_classes),), cls, dtype=torch.long, device=device)
            fake_images = generator(noise, labels)
            all_images.append(fake_images.cpu().numpy())
    
    return np.concatenate(all_images, axis=0)
