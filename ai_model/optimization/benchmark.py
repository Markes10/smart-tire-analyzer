"""
Inference Benchmark - Standalone latency and throughput profiling for TFLite variants.
Run this after TurboQuant optimization to compare model sizes and speeds.

Usage:
  python ai_model/optimization/benchmark.py --models_dir ai_model/saved_models/
  python ai_model/optimization/benchmark.py --model model_fp16.tflite --runs 100
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

PathLike: TypeAlias = str | Path
BenchmarkScalar: TypeAlias = str | int | float
BenchmarkResult: TypeAlias = dict[str, BenchmarkScalar]
BenchmarkSuite: TypeAlias = dict[str, BenchmarkResult]
Float32Array: TypeAlias = npt.NDArray[np.float32]
Float64Array: TypeAlias = npt.NDArray[np.float64]
TFLiteTensorDetail: TypeAlias = Mapping[str, Any]


def _result_number(result: BenchmarkResult, key: str) -> float:
    """Read a numeric metric from a benchmark result."""
    value = result.get(key, 0.0)
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def benchmark_tflite(
    model_path: PathLike,
    n_warmup: int = 10,
    n_runs: int = 50,
    batch_size: int = 1,
) -> BenchmarkResult:
    """
    Benchmark a TFLite model's inference latency.

    Args:
        model_path: Path to .tflite file
        n_warmup: Warmup runs excluded from stats
        n_runs: Timed inference runs
        batch_size: Batch size for inference

    Returns:
        Dictionary with latency stats, model size, and throughput
    """
    import tensorflow as tf

    path = Path(model_path)
    if not path.exists():
        logger.error("Model not found: %s", path)
        return {"error": f"File not found: {path}"}

    logger.info("Benchmarking: %s", path.name)

    tf_module: Any = tf
    interpreter: Any = tf_module.lite.Interpreter(model_path=str(path))
    interpreter.allocate_tensors()

    input_details_any: Any = interpreter.get_input_details()
    output_details_any: Any = interpreter.get_output_details()
    input_details = cast(list[TFLiteTensorDetail], input_details_any)
    output_details = cast(list[TFLiteTensorDetail], output_details_any)

    dummy_inputs: dict[int, Any] = {}
    for detail in input_details:
        shape = [int(dim) for dim in cast(Sequence[Any], detail["shape"])]
        if shape and shape[0] == 1:
            shape[0] = batch_size

        tensor_index = int(detail["index"])
        tensor_dtype = np.dtype(detail["dtype"])
        dummy_inputs[tensor_index] = np.zeros(tuple(shape), dtype=tensor_dtype)

    for _ in range(n_warmup):
        for tensor_index, tensor_data in dummy_inputs.items():
            interpreter.set_tensor(tensor_index, tensor_data)
        interpreter.invoke()

    latencies_ms: list[float] = []
    for _ in range(n_runs):
        for tensor_index, tensor_data in dummy_inputs.items():
            interpreter.set_tensor(tensor_index, tensor_data)
        t0 = time.perf_counter()
        interpreter.invoke()
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000.0)

    arr: Float64Array = np.asarray(latencies_ms, dtype=np.float64)
    size_mb = path.stat().st_size / (1024.0 * 1024.0)
    throughput = 1000.0 / float(np.mean(arr))

    result: BenchmarkResult = {
        "model": path.name,
        "size_mb": round(size_mb, 2),
        "batch_size": batch_size,
        "n_runs": n_runs,
        "latency_mean_ms": round(float(np.mean(arr)), 2),
        "latency_p50_ms": round(float(np.percentile(arr, 50)), 2),
        "latency_p95_ms": round(float(np.percentile(arr, 95)), 2),
        "latency_p99_ms": round(float(np.percentile(arr, 99)), 2),
        "latency_min_ms": round(float(np.min(arr)), 2),
        "latency_max_ms": round(float(np.max(arr)), 2),
        "latency_std_ms": round(float(np.std(arr)), 2),
        "throughput_fps": round(throughput, 1),
        "n_inputs": len(input_details),
        "n_outputs": len(output_details),
    }

    logger.info(
        "  Size: %.2fMB | Mean: %sms | P95: %sms | FPS: %s",
        size_mb,
        result["latency_mean_ms"],
        result["latency_p95_ms"],
        result["throughput_fps"],
    )
    return result


def benchmark_all_variants(
    models_dir: PathLike = "ai_model/saved_models",
    n_runs: int = 50,
    output_path: PathLike | None = None,
) -> BenchmarkSuite:
    """
    Benchmark all TFLite variants in the saved models directory.

    Compares FP32 vs FP16 vs INT8:
    - Size reduction
    - Latency improvement
    - Throughput (FPS)
    """
    models_dir_path = Path(models_dir)
    tflite_files: list[Path] = sorted(models_dir_path.glob("*.tflite"))

    if not tflite_files:
        logger.warning("No .tflite files found in %s", models_dir_path)
        logger.info("Run: python ai_model/optimization/quantize.py --model <model.h5>")
        return {}

    logger.info("\n%s", "=" * 60)
    logger.info("  Smart Tire Benchmark - %d models", len(tflite_files))
    logger.info("%s", "=" * 60)

    results: BenchmarkSuite = {}
    for model_file in tflite_files:
        results[model_file.stem] = benchmark_tflite(model_file, n_runs=n_runs)

    _print_comparison_table(results)

    output_path_obj = (
        Path(output_path)
        if output_path is not None
        else models_dir_path / "benchmark_report.json"
    )
    with output_path_obj.open("w", encoding="utf-8") as file_obj:
        json.dump(results, file_obj, indent=2)
    logger.info("\nBenchmark report saved: %s", output_path_obj)

    return results


def _print_comparison_table(results: BenchmarkSuite) -> None:
    """Print a nicely formatted comparison table."""
    if not results:
        return

    print(f"\n{'Model':<25} {'Size(MB)':>10} {'Mean(ms)':>10} {'P95(ms)':>10} {'FPS':>8}")
    print("-" * 65)

    sorted_results: list[tuple[str, BenchmarkResult]] = sorted(
        results.items(),
        key=lambda item: -_result_number(item[1], "size_mb"),
    )

    for name, result in sorted_results:
        if "error" in result:
            print(f"  {name:<23} {'ERROR':>10}")
            continue

        print(
            f"  {name:<23} "
            f"{_result_number(result, 'size_mb'):>10.2f} "
            f"{_result_number(result, 'latency_mean_ms'):>10.2f} "
            f"{_result_number(result, 'latency_p95_ms'):>10.2f} "
            f"{_result_number(result, 'throughput_fps'):>8.1f}"
        )

    sizes: dict[str, float] = {
        name: _result_number(result, "size_mb")
        for name, result in results.items()
        if "error" not in result
    }
    if sizes:
        baseline_key = max(sizes, key=lambda name: sizes[name])
        baseline_size = sizes[baseline_key]
        print(f"\n  Compression vs {baseline_key}:")
        for name, size in sizes.items():
            if name != baseline_key and size > 0.0:
                ratio = baseline_size / size
                print(f"    {name}: {ratio:.1f}x smaller")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark Smart Tire TFLite models")
    parser.add_argument(
        "--models_dir",
        default="ai_model/saved_models",
        help="Directory with .tflite files",
    )
    parser.add_argument("--model", default=None, help="Single model path to benchmark")
    parser.add_argument("--runs", type=int, default=50, help="Number of timed runs")
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    if args.model:
        result = benchmark_tflite(args.model, n_runs=args.runs)
        print(json.dumps(result, indent=2))
    else:
        benchmark_all_variants(args.models_dir, n_runs=args.runs, output_path=args.output)
