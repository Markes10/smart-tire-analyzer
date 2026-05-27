"""
TurboQuant optimization: quantization, optional pruning, TFLite export, and benchmarking.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt
import tensorflow as tf

from ai_model.optimization.benchmark import BenchmarkResult, BenchmarkSuite
from ai_model.optimization.pruning import ModelPruner

logger = logging.getLogger(__name__)

SAVED_MODELS_DIR = Path("ai_model/saved_models")

PathLike: TypeAlias = str | Path
KerasModel: TypeAlias = Any
TFLiteDetail: TypeAlias = dict[str, Any]
Float32Array: TypeAlias = npt.NDArray[np.float32]
Float64Array: TypeAlias = npt.NDArray[np.float64]
RepresentativeBatch: TypeAlias = list[Float32Array]
RepresentativeDatasetFn: TypeAlias = Callable[[], Iterator[RepresentativeBatch]]


def _result_number(result: BenchmarkResult, key: str) -> float:
    """Read a numeric metric from a benchmark result."""
    value = result.get(key, 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


class TurboQuantOptimizer:
    """
    Complete optimization pipeline for Smart Tire models.

    Steps:
    1. Post-training quantization (INT8 or FP16)
    2. Optional model pruning
    3. TFLite export for mobile deployment
    4. Benchmarking for speed and size comparisons
    """

    def __init__(
        self,
        model_path: PathLike,
        output_dir: PathLike = SAVED_MODELS_DIR,
        representative_dataset_fn: RepresentativeDatasetFn | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.representative_dataset_fn = representative_dataset_fn
        self.model: KerasModel | None = None
        self._pruner: ModelPruner | None = None

    def _load_model_from_path(self, path: PathLike) -> KerasModel:
        """Load a Keras model from disk through a narrow untyped boundary."""
        tf_module: Any = tf
        model: Any = tf_module.keras.models.load_model(str(Path(path)))
        return model

    def _ensure_model_loaded(self) -> KerasModel:
        """Return the current model, loading it from disk if necessary."""
        if self.model is None:
            self.load_model()
        return self.model

    def _convert_model(
        self,
        model: KerasModel,
        configure_converter: Callable[[Any], None] | None = None,
    ) -> bytes:
        """
        Convert a Keras model to TFLite bytes through a temporary SavedModel export.

        This avoids a TensorFlow/Keras crash seen with `from_keras_model` in some
        TF 2.16 / Keras 3 environments.
        """
        tf_module: Any = tf
        model_obj: Any = model

        with tempfile.TemporaryDirectory() as temp_dir:
            export_dir = Path(temp_dir) / "saved_model"
            if hasattr(model_obj, "export"):
                model_obj.export(str(export_dir))
            else:
                tf_module.saved_model.save(model_obj, str(export_dir))

            converter: Any = tf_module.lite.TFLiteConverter.from_saved_model(
                str(export_dir)
            )
            if configure_converter is not None:
                configure_converter(converter)
            return bytes(converter.convert())

    def _write_tflite_bytes(self, out_path: Path, tflite_bytes: bytes) -> str:
        """Persist converted TFLite bytes and return the saved path."""
        with out_path.open("wb") as file_obj:
            file_obj.write(tflite_bytes)
        return str(out_path)

    def load_model(self) -> KerasModel:
        """Load the source model from .h5, .keras, or SavedModel path."""
        logger.info("Loading model from: %s", self.model_path)
        model = self._load_model_from_path(self.model_path)
        self.model = model
        param_count = int(model.count_params())
        logger.info("Model loaded. Params: %s", f"{param_count:,}")
        return model

    def quantize_fp16(self, input_model_path: PathLike | None = None) -> str:
        """
        Convert a model to FP16 precision.

        Returns:
            Path to the saved `.tflite` file.
        """
        path = Path(input_model_path) if input_model_path is not None else self.model_path
        model = self._load_model_from_path(path)
        tf_module: Any = tf

        def configure_converter(converter: Any) -> None:
            converter.optimizations = [tf_module.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]

        tflite_model = self._convert_model(model, configure_converter)
        out_path = self.output_dir / "model_fp16.tflite"
        self._write_tflite_bytes(out_path, tflite_model)

        size_mb = out_path.stat().st_size / (1024.0 * 1024.0)
        logger.info("FP16 model saved: %s (%.2f MB)", out_path, size_mb)
        return str(out_path)

    def _default_calibration_dataset(
        self,
        n_samples: int = 100,
    ) -> Iterator[RepresentativeBatch]:
        """Build a synthetic representative dataset from the model input shapes."""
        model = self._ensure_model_loaded()
        model_inputs = cast(list[Any], model.inputs)

        for _ in range(n_samples):
            batch: RepresentativeBatch = []
            for input_tensor in model_inputs:
                shape = [
                    int(dim) if dim is not None else 1
                    for dim in cast(Sequence[Any], input_tensor.shape)
                ]
                if shape:
                    shape[0] = 1
                input_array: Float32Array = np.random.randn(*shape).astype(np.float32)
                batch.append(input_array)
            yield batch

    def quantize_int8(
        self,
        input_model_path: PathLike | None = None,
        n_calibration_samples: int = 100,
    ) -> str:
        """
        Perform full integer quantization.

        Returns:
            Path to the saved `.tflite` file.
        """
        path = Path(input_model_path) if input_model_path is not None else self.model_path
        model = self._load_model_from_path(path)
        self.model = model
        tf_module: Any = tf

        if self.representative_dataset_fn is not None:
            representative_dataset = self.representative_dataset_fn
        else:
            logger.warning(
                "No representative dataset provided; using synthetic calibration inputs"
            )

            def synthetic_dataset() -> Iterator[RepresentativeBatch]:
                return self._default_calibration_dataset(
                    n_samples=n_calibration_samples
                )

            representative_dataset = synthetic_dataset

        def configure_converter(converter: Any) -> None:
            converter.optimizations = [tf_module.lite.Optimize.DEFAULT]
            converter.target_spec.supported_ops = [
                tf_module.lite.OpsSet.TFLITE_BUILTINS_INT8
            ]
            converter.inference_input_type = tf.int8
            converter.inference_output_type = tf.int8
            converter.representative_dataset = representative_dataset

        tflite_model = self._convert_model(model, configure_converter)
        out_path = self.output_dir / "model_int8.tflite"
        self._write_tflite_bytes(out_path, tflite_model)

        size_mb = out_path.stat().st_size / (1024.0 * 1024.0)
        logger.info("INT8 model saved: %s (%.2f MB)", out_path, size_mb)
        return str(out_path)

    def prune_model(
        self,
        target_sparsity: float = 0.5,
        begin_step: int = 0,
        end_step: int = 1000,
        frequency: int = 100,
    ) -> KerasModel:
        """
        Apply magnitude-based pruning through the shared pruning helper.

        Returns:
            The pruned model, or the original model if pruning is unavailable.
        """
        model = self._ensure_model_loaded()
        self._pruner = ModelPruner(model)
        pruned_model = self._pruner.apply_pruning(
            target_sparsity=target_sparsity,
            begin_step=begin_step,
            end_step=end_step,
            frequency=frequency,
        )

        if pruned_model is model:
            logger.info("Pruning step skipped; continuing with the loaded model")
        else:
            logger.info("Model pruned to %.0f%% sparsity target", target_sparsity * 100.0)

        return pruned_model

    def strip_pruning_and_export(self, pruned_model: KerasModel) -> str:
        """Strip pruning wrappers and export a clean TFLite model."""
        pruner = self._pruner or ModelPruner(pruned_model)
        stripped_model = pruner.strip_pruning(pruned_model)

        tf_module: Any = tf

        def configure_converter(converter: Any) -> None:
            converter.optimizations = [tf_module.lite.Optimize.DEFAULT]

        tflite_bytes = self._convert_model(stripped_model, configure_converter)

        out_path = self.output_dir / "model_pruned.tflite"
        self._write_tflite_bytes(out_path, tflite_bytes)

        size_mb = out_path.stat().st_size / (1024.0 * 1024.0)
        logger.info("Pruned TFLite saved: %s (%.2f MB)", out_path, size_mb)
        return str(out_path)

    def export_tflite_standard(self, input_model_path: PathLike | None = None) -> str:
        """Export a standard FP32 TFLite model."""
        path = Path(input_model_path) if input_model_path is not None else self.model_path
        model = self._load_model_from_path(path)

        tflite_bytes = self._convert_model(model)

        out_path = self.output_dir / "model_latest.tflite"
        self._write_tflite_bytes(out_path, tflite_bytes)

        size_mb = out_path.stat().st_size / (1024.0 * 1024.0)
        logger.info("Standard TFLite saved: %s (%.2f MB)", out_path, size_mb)
        return str(out_path)

    def benchmark_tflite(
        self,
        tflite_path: PathLike,
        n_runs: int = 50,
        warmup_runs: int = 5,
    ) -> BenchmarkResult:
        """
        Benchmark TFLite inference latency.

        Returns:
            A dictionary of latency and size metrics.
        """
        path = Path(tflite_path)
        tf_module: Any = tf
        interpreter: Any = tf_module.lite.Interpreter(model_path=str(path))
        interpreter.allocate_tensors()

        input_details = cast(list[TFLiteDetail], interpreter.get_input_details())

        dummy_inputs: dict[int, Any] = {}
        for detail in input_details:
            shape = [int(dim) for dim in cast(Sequence[Any], detail["shape"])]
            tensor_dtype = np.dtype(detail["dtype"])
            dummy_inputs[int(detail["index"])] = np.zeros(
                tuple(shape),
                dtype=tensor_dtype,
            )

        for _ in range(warmup_runs):
            for tensor_index, tensor_data in dummy_inputs.items():
                interpreter.set_tensor(tensor_index, tensor_data)
            interpreter.invoke()

        latencies_ms: list[float] = []
        for _ in range(n_runs):
            for tensor_index, tensor_data in dummy_inputs.items():
                interpreter.set_tensor(tensor_index, tensor_data)
            start = time.perf_counter()
            interpreter.invoke()
            end = time.perf_counter()
            latencies_ms.append((end - start) * 1000.0)

        latencies: Float64Array = np.asarray(latencies_ms, dtype=np.float64)
        size_mb = path.stat().st_size / (1024.0 * 1024.0)

        results: BenchmarkResult = {
            "model": str(path),
            "size_mb": round(size_mb, 2),
            "n_runs": n_runs,
            "latency_mean_ms": round(float(np.mean(latencies)), 2),
            "latency_p50_ms": round(float(np.percentile(latencies, 50)), 2),
            "latency_p95_ms": round(float(np.percentile(latencies, 95)), 2),
            "latency_p99_ms": round(float(np.percentile(latencies, 99)), 2),
            "latency_min_ms": round(float(np.min(latencies)), 2),
            "latency_max_ms": round(float(np.max(latencies)), 2),
        }

        logger.info(
            "Benchmark: %sms mean (%d runs, %.1fMB)",
            results["latency_mean_ms"],
            n_runs,
            size_mb,
        )
        return results

    def run_full_optimization(self) -> BenchmarkSuite:
        """
        Run the complete optimization pipeline.

        Returns:
            Benchmark results for each successfully exported variant.
        """
        self.load_model()
        results: BenchmarkSuite = {}

        logger.info("=== TurboQuant Optimization Pipeline ===")

        try:
            fp16_path = self.quantize_fp16()
            results["fp16"] = self.benchmark_tflite(fp16_path)
        except Exception as exc:
            logger.error("FP16 quantization failed: %s", exc)

        try:
            int8_path = self.quantize_int8()
            results["int8"] = self.benchmark_tflite(int8_path)
        except Exception as exc:
            logger.error("INT8 quantization failed: %s", exc)

        try:
            standard_path = self.export_tflite_standard()
            results["standard"] = self.benchmark_tflite(standard_path)
        except Exception as exc:
            logger.error("Standard TFLite export failed: %s", exc)

        report_path = self.output_dir / "benchmark_report.json"
        with report_path.open("w", encoding="utf-8") as file_obj:
            json.dump(results, file_obj, indent=2)
        logger.info("Benchmark report saved: %s", report_path)

        return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TurboQuant model optimizer")
    parser.add_argument("--model", required=True, help="Path to the source Keras model")
    parser.add_argument(
        "--output",
        default=str(SAVED_MODELS_DIR),
        help="Directory where optimized models should be written",
    )
    args = parser.parse_args()

    optimizer = TurboQuantOptimizer(model_path=args.model, output_dir=args.output)
    results = optimizer.run_full_optimization()

    print("\n=== TURBOQUANT BENCHMARK RESULTS ===")
    for variant, stats in results.items():
        print(f"\n[{variant.upper()}]")
        print(f"  Size:    {_result_number(stats, 'size_mb'):.2f} MB")
        print(
            "  Latency: "
            f"{_result_number(stats, 'latency_mean_ms'):.2f}ms mean / "
            f"{_result_number(stats, 'latency_p95_ms'):.2f}ms p95"
        )
