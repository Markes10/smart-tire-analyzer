"""
GradCAM Heatmap Visualization for Smart Tire CNN.
Generates class activation maps to explain which tire regions
the model focuses on for each prediction.
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

logger = logging.getLogger(__name__)

PathLike: TypeAlias = str | Path
FloatArray: TypeAlias = npt.NDArray[np.float32]
UInt8Array: TypeAlias = npt.NDArray[np.uint8]


def _load_matplotlib() -> tuple[Any, Any, Any]:
    """Import matplotlib lazily so this module works without plotting deps."""
    try:
        matplotlib = importlib.import_module("matplotlib")
        matplotlib.use("Agg")
        pyplot = importlib.import_module("matplotlib.pyplot")
        colors = importlib.import_module("matplotlib.colors")
        cm_module = importlib.import_module("matplotlib.cm")
        return pyplot, colors, cm_module
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "matplotlib is required for GradCAM visualization. "
            "Install it in the project virtual environment to enable plotting."
        ) from exc


class GradCAM:
    """
    Gradient-weighted Class Activation Mapping for MobileNetV2.

    Produces heatmaps showing which parts of the tire image the CNN
    focuses on for its wear pattern and tread depth predictions.
    """

    def __init__(
        self,
        model: Any,
        last_conv_layer_name: str = "out_relu",
    ) -> None:
        self.model: Any = model
        self.last_conv_layer_name = last_conv_layer_name
        self._grad_model: Any | None = None

    def _build_grad_model(self) -> None:
        """Build GradCAM sub-model up to the last conv layer."""
        try:
            cnn_extractor = self.model.get_layer("mobilenetv2_extractor")
            cnn_model = cnn_extractor.get_layer("mobilenet_v2")
            last_conv = cnn_model.get_layer(self.last_conv_layer_name)
            self._grad_model = tf.keras.Model(
                inputs=self.model.inputs,
                outputs=[last_conv.output, self.model.output],
            )
        except Exception as exc:
            logger.warning("GradCAM model build failed: %s - using approximate method", exc)
            self._grad_model = None

    def compute_heatmap(
        self,
        image: npt.ArrayLike,
        target_output: str = "wear_pattern",
        class_idx: int | None = None,
    ) -> FloatArray | None:
        """
        Generate GradCAM heatmap for a given image.

        Args:
            image: Preprocessed image (224, 224, 4) float32
            target_output: Which model output to explain ("wear_pattern", "health_score")
            class_idx: Class index to explain (for classification). None = argmax.

        Returns:
            heatmap: (H, W) float32 array in [0, 1], or None if failed
        """
        if self._grad_model is None:
            self._build_grad_model()
        if self._grad_model is None:
            return None

        image_arr = np.asarray(image, dtype=np.float32)
        image_height, image_width = int(image_arr.shape[0]), int(image_arr.shape[1])
        img_tensor = tf.expand_dims(tf.convert_to_tensor(image_arr, dtype=tf.float32), 0)

        with tf.GradientTape() as tape:
            grad_outputs: Any = self._grad_model(img_tensor)
            conv_outputs: Any = grad_outputs[0]
            predictions_raw: Any = grad_outputs[1]

            if not isinstance(predictions_raw, Mapping):
                logger.warning("GradCAM predictions are not a mapping; cannot select target output")
                return None

            predictions = cast(Mapping[str, Any], predictions_raw)

            loss: Any
            if target_output == "wear_pattern" and "wear_pattern" in predictions:
                target_tensor: Any = predictions["wear_pattern"]
                selected_class = class_idx
                if selected_class is None:
                    selected_class = int(tf.argmax(target_tensor[0]).numpy())
                loss = target_tensor[:, selected_class]
            elif "health_score" in predictions:
                loss = predictions["health_score"]
            else:
                logger.warning("GradCAM target output '%s' not available in predictions", target_output)
                return None

        tf_core: Any = tf
        gradient_tape: Any = tape
        grads = gradient_tape.gradient(loss, conv_outputs)
        if grads is None:
            logger.warning("GradCAM gradients could not be computed")
            return None

        pooled_grads: Any = tf_core.reduce_mean(grads, axis=(0, 1, 2))
        conv_output: Any = conv_outputs[0]
        channel_weights: Any = tf_core.reshape(pooled_grads, (1, 1, -1))
        heatmap_tensor: Any = tf_core.reduce_sum(
            conv_output * channel_weights,
            axis=-1,
        )
        heatmap_tensor = tf_core.maximum(heatmap_tensor, 0.0)

        max_value = float(tf_core.reduce_max(heatmap_tensor).numpy())
        if max_value > 0.0:
            heatmap_tensor = heatmap_tensor / max_value

        heatmap_base = np.asarray(heatmap_tensor.numpy(), dtype=np.float32)
        heatmap_image: Any = tf_core.convert_to_tensor(
            np.expand_dims(heatmap_base, axis=-1),
            dtype=tf.float32,
        )
        heatmap_resized: Any = tf_core.image.resize(heatmap_image, [image_height, image_width])
        return np.asarray(heatmap_resized.numpy()[..., 0], dtype=np.float32)

    def overlay_heatmap(
        self,
        image: npt.ArrayLike,
        heatmap: npt.ArrayLike,
        alpha: float = 0.4,
        colormap: str = "jet",
    ) -> UInt8Array:
        """
        Overlay heatmap on original image.

        Args:
            image: Original image (H, W, 3 or 4) uint8 or float32
            heatmap: GradCAM heatmap (H, W) in [0, 1]
            alpha: Heatmap transparency (0=invisible, 1=fully visible)

        Returns:
            Overlaid image (H, W, 3) uint8
        """
        image_arr = np.asarray(image)
        heatmap_arr = np.asarray(heatmap, dtype=np.float32)

        if image_arr.dtype != np.uint8:
            image_rgb = np.clip(image_arr[:, :, :3] * 255.0, 0.0, 255.0).astype(np.uint8)
        else:
            image_rgb = image_arr[:, :, :3].astype(np.uint8, copy=False)

        _, _, cm_module = _load_matplotlib()
        cmap = cm_module.get_cmap(colormap)
        colored = np.asarray(cmap(heatmap_arr)[..., :3] * 255.0, dtype=np.uint8)

        blended = np.clip(
            alpha * colored.astype(np.float32) + (1.0 - alpha) * image_rgb.astype(np.float32),
            0.0,
            255.0,
        ).astype(np.uint8)
        return blended

    def generate_and_save(
        self,
        image: npt.ArrayLike,
        output_path: PathLike | None = None,
        title: str = "GradCAM Tire Analysis",
    ) -> str | None:
        """
        Generate GradCAM visualization and save to file.

        Args:
            image: Preprocessed tire image (H, W, 4)
            output_path: Output .png path (auto-generated if None)
            title: Plot title

        Returns:
            Path to saved plot, or None if failed
        """
        heatmap = self.compute_heatmap(image)
        if heatmap is None:
            logger.warning("GradCAM heatmap generation failed")
            return None

        image_arr = np.asarray(image, dtype=np.float32)
        overlaid = self.overlay_heatmap(image_arr, heatmap)
        plt, colors, cm_module = _load_matplotlib()

        subplot_result: Any = plt.subplots(1, 3, figsize=(15, 5))
        fig = subplot_result[0]
        axes = subplot_result[1]
        ax_original: Any = axes[0]
        ax_heatmap: Any = axes[1]
        ax_overlay: Any = axes[2]
        fig.suptitle(title, fontsize=14, fontweight="bold")

        original_rgb = np.clip(image_arr[:, :, :3], 0.0, 1.0)
        ax_original.imshow(original_rgb)
        ax_original.set_title("Original Image", fontsize=11)
        ax_original.axis("off")

        ax_heatmap.imshow(heatmap, cmap="jet")
        ax_heatmap.set_title("GradCAM Heatmap", fontsize=11)
        ax_heatmap.axis("off")

        ax_overlay.imshow(overlaid)
        ax_overlay.set_title("Overlay (Focus Regions)", fontsize=11)
        ax_overlay.axis("off")

        scalar_mappable = cm_module.ScalarMappable(
            cmap=cm_module.get_cmap("jet"),
            norm=colors.Normalize(vmin=0.0, vmax=1.0),
        )
        fig.colorbar(scalar_mappable, ax=ax_heatmap, fraction=0.046, pad=0.04, label="Attention")

        fig.tight_layout()

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path_obj = (
            Path(output_path)
            if output_path is not None
            else Path("logs/inference") / f"gradcam_{timestamp}.png"
        )
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        fig.savefig(output_path_obj, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("GradCAM saved: %s", output_path_obj)
        return str(output_path_obj)
