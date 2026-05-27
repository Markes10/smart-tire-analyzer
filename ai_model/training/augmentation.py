"""
Albumentations augmentation pipeline for tire training images.
Implements all augmentation strategies from the preprocessing spec.
"""

from __future__ import annotations

# pyright: reportMissingTypeStubs=false

from typing import Any, TypeAlias

import albumentations as A
import cv2
import numpy as np
import numpy.typing as npt

UInt8Image: TypeAlias = npt.NDArray[np.uint8]
UInt8Batch: TypeAlias = npt.NDArray[np.uint8]
AlbumentationsCompose: TypeAlias = Any


def _as_uint8_image(image: npt.ArrayLike) -> UInt8Image:
    """Normalize an image-like object to a uint8 NumPy array."""
    return np.asarray(image, dtype=np.uint8)


class TireAugmentationPipeline:
    """
    Complete augmentation pipeline tailored for tire images.

    Rules from preprocessing spec:
    - SAFE:    Brightness, contrast, horizontal flip, rotation +/-15 degrees
    - CAREFUL: Zoom (tread is directional), vertical flip
    - NEVER:   180 degree rotation (unnatural tire appearance)
    """

    def __init__(
        self,
        training: bool = True,
        severity: str = "standard",
        image_size: tuple[int, int] = (224, 224),
    ) -> None:
        self.training = training
        self.severity = severity
        self.image_size = image_size
        self.transform: AlbumentationsCompose = self._build_transform()

    def _build_transform(self) -> AlbumentationsCompose:
        albumentations: Any = A

        if not self.training:
            return albumentations.Compose([])

        if self.severity == "light":
            return albumentations.Compose(
                [
                    albumentations.HorizontalFlip(p=0.5),
                    albumentations.RandomBrightnessContrast(
                        brightness_limit=0.1,
                        contrast_limit=0.1,
                        p=0.4,
                    ),
                    albumentations.Rotate(
                        limit=10,
                        p=0.3,
                        border_mode=cv2.BORDER_REFLECT_101,
                    ),
                ]
            )

        if self.severity == "heavy":
            return albumentations.Compose(
                [
                    albumentations.HorizontalFlip(p=0.5),
                    albumentations.VerticalFlip(
                        p=0.1
                    ),  # Careful: tread is directional.
                    albumentations.RandomBrightnessContrast(
                        brightness_limit=0.35,
                        contrast_limit=0.35,
                        p=0.6,
                    ),
                    albumentations.Rotate(
                        limit=15,
                        p=0.6,
                        border_mode=cv2.BORDER_REFLECT_101,
                    ),
                    albumentations.RandomScale(scale_limit=0.15, p=0.4),
                    albumentations.GaussNoise(var_limit=(10.0, 50.0), p=0.4),
                    albumentations.MotionBlur(blur_limit=5, p=0.2),
                    albumentations.CoarseDropout(
                        max_holes=6,
                        max_height=20,
                        max_width=20,
                        p=0.3,
                    ),
                    albumentations.HueSaturationValue(
                        hue_shift_limit=10,
                        sat_shift_limit=20,
                        val_shift_limit=20,
                        p=0.4,
                    ),
                    albumentations.ElasticTransform(alpha=50, sigma=7, p=0.2),
                    albumentations.GridDistortion(
                        num_steps=4,
                        distort_limit=0.25,
                        p=0.2,
                    ),
                    albumentations.CLAHE(
                        clip_limit=3.0,
                        tile_grid_size=(8, 8),
                        p=0.3,
                    ),
                    albumentations.RandomShadow(
                        shadow_roi=(0, 0.3, 1, 1),
                        p=0.2,
                    ),
                    albumentations.RandomRain(
                        blur_value=2,
                        p=0.15,
                    ),  # Simulate wet road conditions.
                ]
            )

        return albumentations.Compose(
            [
                albumentations.HorizontalFlip(p=0.5),
                albumentations.RandomBrightnessContrast(
                    brightness_limit=0.25,
                    contrast_limit=0.25,
                    p=0.5,
                ),
                albumentations.Rotate(
                    limit=15,
                    p=0.5,
                    border_mode=cv2.BORDER_REFLECT_101,
                ),
                albumentations.RandomScale(scale_limit=0.10, p=0.3),
                albumentations.GaussNoise(var_limit=(5.0, 30.0), p=0.3),
                albumentations.CoarseDropout(
                    max_holes=4,
                    max_height=16,
                    max_width=16,
                    p=0.2,
                ),
                albumentations.HueSaturationValue(
                    hue_shift_limit=5,
                    sat_shift_limit=15,
                    val_shift_limit=15,
                    p=0.3,
                ),
                albumentations.ElasticTransform(alpha=30, sigma=5, p=0.15),
                albumentations.GridDistortion(
                    num_steps=3,
                    distort_limit=0.2,
                    p=0.15,
                ),
                albumentations.CLAHE(
                    clip_limit=2.0,
                    tile_grid_size=(8, 8),
                    p=0.25,
                ),
            ]
        )

    def __call__(self, image: UInt8Image) -> UInt8Image:
        """Apply augmentation to a single image."""
        normalized_image = _as_uint8_image(image)
        if not self.training:
            return normalized_image

        transformed: Any = self.transform(image=normalized_image)
        return _as_uint8_image(transformed["image"])

    def augment_batch(self, images: UInt8Batch) -> UInt8Batch:
        """Apply augmentation to a batch of images."""
        augmented: list[UInt8Image] = [self(_as_uint8_image(image)) for image in images]
        return np.asarray(augmented, dtype=np.uint8)


def generate_synthetic_tire(
    base_image: UInt8Image,
    n_variants: int = 5,
    seed: int | None = None,
) -> list[UInt8Image]:
    """
    Generate synthetic tire variants from a single real image.

    Used to augment rare wear pattern classes.
    """
    if seed is not None:
        np.random.seed(seed)

    source_image = _as_uint8_image(base_image)
    heavy_aug = TireAugmentationPipeline(training=True, severity="heavy")
    variants: list[UInt8Image] = [heavy_aug(source_image.copy()) for _ in range(n_variants)]
    return variants
