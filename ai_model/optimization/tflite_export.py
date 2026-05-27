"""
TFLite export utilities for Keras models.
"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

logger = logging.getLogger(__name__)

PathLike: TypeAlias = str | Path
KerasModel: TypeAlias = Any
InputShape: TypeAlias = Sequence[int | None]
InputShapes: TypeAlias = Sequence[InputShape]
Float32Array: TypeAlias = npt.NDArray[np.float32]
RepresentativeBatch: TypeAlias = list[Float32Array]
RepresentativeDatasetFn: TypeAlias = Callable[[], Iterator[RepresentativeBatch]]
TFLiteTensorDetail: TypeAlias = Mapping[str, Any]
VerificationInfo: TypeAlias = dict[str, Any]


def _normalise_shape(shape_like: Sequence[Any]) -> list[int]:
    """Convert a tensor shape to concrete positive integers."""
    shape: list[int] = []
    for dim in shape_like:
        dim_int = int(dim) if dim is not None else 1
        shape.append(dim_int if dim_int > 0 else 1)
    return shape


def _export_saved_model(model: KerasModel, export_dir: Path) -> None:
    """Export a Keras model to a SavedModel directory."""
    tf_module: Any = tf
    model_obj: Any = model

    if hasattr(model_obj, "export"):
        model_obj.export(str(export_dir))
    else:
        tf_module.saved_model.save(model_obj, str(export_dir))


def _convert_model_to_tflite_bytes(
    model: KerasModel,
    quantize: bool = False,
    quantization_type: str = "fp16",
    representative_dataset_fn: RepresentativeDatasetFn | None = None,
) -> bytes:
    """Convert a Keras model to TFLite bytes through a temporary SavedModel."""
    tf_module: Any = tf
    quantization_key = quantization_type.lower()

    with tempfile.TemporaryDirectory() as temp_dir:
        export_dir = Path(temp_dir) / "saved_model"
        _export_saved_model(model, export_dir)

        converter: Any = tf_module.lite.TFLiteConverter.from_saved_model(str(export_dir))

        if quantize:
            converter.optimizations = [tf_module.lite.Optimize.DEFAULT]

            if quantization_key == "fp16":
                converter.target_spec.supported_types = [tf.float16]
                logger.info("Applying FP16 quantization")
            elif quantization_key == "int8":
                converter.target_spec.supported_ops = [
                    tf_module.lite.OpsSet.TFLITE_BUILTINS_INT8
                ]
                converter.inference_input_type = tf.float32
                converter.inference_output_type = tf.float32

                if representative_dataset_fn is not None:
                    converter.representative_dataset = representative_dataset_fn
                    logger.info("Applying INT8 quantization with calibration data")
                else:
                    logger.warning(
                        "INT8 quantization requested without calibration data"
                    )
            else:
                raise ValueError(
                    "quantization_type must be 'fp16' or 'int8', "
                    f"got {quantization_type!r}"
                )

        return bytes(converter.convert())


def export_to_tflite(
    model: KerasModel,
    output_path: PathLike,
    input_shapes: InputShapes | None = None,
    quantize: bool = False,
    quantization_type: str = "fp16",
    representative_dataset_fn: RepresentativeDatasetFn | None = None,
) -> str:
    """
    Export a Keras model to TFLite format.

    Args:
        model: Keras model to export.
        output_path: Output `.tflite` file path.
        input_shapes: Optional input shape hints kept for API compatibility.
        quantize: Whether to apply quantization.
        quantization_type: `"fp16"` or `"int8"`.
        representative_dataset_fn: Calibration dataset for INT8 export.

    Returns:
        Path to the saved `.tflite` file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if input_shapes is not None:
        logger.info("Received %d input shape hint(s) for export", len(input_shapes))

    logger.info("Exporting model to TFLite: %s", path)
    tflite_bytes = _convert_model_to_tflite_bytes(
        model=model,
        quantize=quantize,
        quantization_type=quantization_type,
        representative_dataset_fn=representative_dataset_fn,
    )

    path.write_bytes(tflite_bytes)

    size_mb = path.stat().st_size / (1024.0 * 1024.0)
    logger.info("TFLite model exported: %s (%.2f MB)", path, size_mb)
    return str(path)


def verify_tflite_model(
    tflite_path: PathLike,
    test_input_shapes: InputShapes | None = None,
) -> tuple[bool, VerificationInfo]:
    """
    Verify a TFLite model loads and runs correctly.

    Returns:
        `(success, info)` where `info` contains tensor metadata or an error.
    """
    path = Path(tflite_path)

    try:
        tf_module: Any = tf
        interpreter: Any = tf_module.lite.Interpreter(model_path=str(path))

        if test_input_shapes is not None:
            initial_input_details = cast(
                list[TFLiteTensorDetail],
                interpreter.get_input_details(),
            )
            for detail, shape_hint in zip(initial_input_details, test_input_shapes):
                interpreter.resize_tensor_input(
                    int(detail["index"]),
                    _normalise_shape(shape_hint),
                    strict=False,
                )

        interpreter.allocate_tensors()

        input_details = cast(list[TFLiteTensorDetail], interpreter.get_input_details())
        output_details = cast(list[TFLiteTensorDetail], interpreter.get_output_details())

        for detail in input_details:
            dummy = np.zeros(
                tuple(_normalise_shape(cast(Sequence[Any], detail["shape"]))),
                dtype=np.dtype(detail["dtype"]),
            )
            interpreter.set_tensor(int(detail["index"]), dummy)

        interpreter.invoke()

        for detail in output_details:
            interpreter.get_tensor(int(detail["index"]))

        info: VerificationInfo = {
            "inputs": [
                {
                    "name": str(detail["name"]),
                    "shape": _normalise_shape(cast(Sequence[Any], detail["shape"])),
                }
                for detail in input_details
            ],
            "outputs": [
                {
                    "name": str(detail["name"]),
                    "shape": _normalise_shape(cast(Sequence[Any], detail["shape"])),
                }
                for detail in output_details
            ],
            "size_mb": round(path.stat().st_size / (1024.0 * 1024.0), 2),
        }
        logger.info("TFLite verification passed: %s", info)
        return True, info

    except Exception as exc:
        logger.error("TFLite verification failed: %s", exc)
        return False, {"error": str(exc)}
