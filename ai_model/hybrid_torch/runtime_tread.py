"""Runtime tread-sequence estimates for the hybrid model.

The production analyzer does not know the real tread depth before inference.
This module therefore creates a conservative visual proxy that can be used as
the BiLSTM input without leaking label values into training or evaluation.
"""

from __future__ import annotations

import cv2
import numpy as np

from ai_model.hybrid_torch.constants import IMAGE_SIZE, TREAD_MAX_MM

RUNTIME_TREAD_SEQUENCE_SOURCE = "runtime_visual_proxy"
VISUAL_TREAD_PRIOR_MM = 4.2


def _center_square_resize(image_bgr: np.ndarray, image_size: int = IMAGE_SIZE) -> np.ndarray:
    height, width = image_bgr.shape[:2]
    side = min(height, width)
    top = max(0, (height - side) // 2)
    left = max(0, (width - side) // 2)
    crop = image_bgr[top : top + side, left : left + side]
    interpolation = cv2.INTER_AREA if side > image_size else cv2.INTER_LINEAR
    return cv2.resize(crop, (image_size, image_size), interpolation=interpolation)


def estimate_visual_tread_depths(image_bgr: np.ndarray) -> list[float]:
    """
    Estimate a four-position tread-depth proxy from image texture.

    A single tire photo has no reliable physical scale, so this intentionally
    keeps the average near a data prior and only lets visual texture adjust the
    left-to-right pattern. It is an input feature for the hybrid model, not a
    standalone tread-gauge measurement.
    """
    if image_bgr is None or image_bgr.size == 0:
        return [VISUAL_TREAD_PRIOR_MM] * 4

    image = _center_square_resize(image_bgr)
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    grad_x = cv2.Scharr(gray, cv2.CV_32F, 1, 0)
    grad_y = cv2.Scharr(gray, cv2.CV_32F, 0, 1)
    edge = cv2.magnitude(grad_x, grad_y)
    edge = edge / (float(np.max(edge)) + 1e-6)

    gray_u8 = np.clip(gray * 255.0, 0, 255).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    blackhat = cv2.morphologyEx(gray_u8, cv2.MORPH_BLACKHAT, kernel).astype(np.float32) / 255.0
    canny = cv2.Canny(gray_u8, 40, 120).astype(np.float32) / 255.0
    local_mean = cv2.blur(gray, (11, 11))
    local_contrast = np.abs(gray - local_mean)
    local_contrast = local_contrast / (float(np.max(local_contrast)) + 1e-6)
    shadow = np.clip(1.0 - gray, 0.0, 1.0)

    groove_cue = (
        edge * 0.35
        + blackhat * 0.30
        + canny * 0.15
        + local_contrast * 0.12
        + shadow * 0.08
    )
    groove_cue = groove_cue / (float(np.max(groove_cue)) + 1e-6)

    band_scores = np.asarray(
        [float(np.mean(band)) for band in np.array_split(groove_cue, 4, axis=1)],
        dtype=np.float32,
    )
    centered = band_scores - float(np.mean(band_scores))

    # Texture strength has weak correlation with absolute depth, but it is still
    # useful for identifying relative side-to-side wear. Keep the correction
    # deliberately small so the model cannot treat this as a hidden label.
    absolute_texture = float(np.mean(band_scores))
    global_adjustment = np.clip((absolute_texture - 0.35) * 0.9, -0.45, 0.45)
    deltas = np.clip(centered * 2.8, -0.9, 0.9)
    depths = np.clip(VISUAL_TREAD_PRIOR_MM + global_adjustment + deltas, 0.8, TREAD_MAX_MM)
    return [float(value) for value in depths]
