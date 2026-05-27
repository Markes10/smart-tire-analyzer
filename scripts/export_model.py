"""
Export Model Script — One-command model export to TFLite variants.
Runs TurboQuant optimization pipeline and prints benchmark results.

Usage:
  python scripts/export_model.py --model ai_model/saved_models/model_best.h5
  python scripts/export_model.py --model model_best.h5 --fp16 --int8 --benchmark
"""

import sys
import json
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(
        description="Export Smart Tire model to TFLite with TurboQuant optimization"
    )
    parser.add_argument("--model", required=True, help="Path to .h5 Keras model")
    parser.add_argument("--output", default="ai_model/saved_models", help="Output directory")
    parser.add_argument("--fp16", action="store_true", default=True, help="Export FP16 quantized (default: on)")
    parser.add_argument("--int8", action="store_true", default=False, help="Export INT8 quantized")
    parser.add_argument("--standard", action="store_true", default=True, help="Export standard FP32 TFLite")
    parser.add_argument("--benchmark", action="store_true", default=True, help="Run benchmark after export")
    parser.add_argument("--benchmark_runs", type=int, default=50, help="Benchmark runs")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"\n❌ Model file not found: {model_path}")
        print("   Train a model first: python ai_model/training/train.py")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(f"  🚗 Smart Tire — TurboQuant Model Export")
    print(f"  Model:  {model_path.name}")
    print(f"  Output: {args.output}")
    print("=" * 60)

    from ai_model.optimization.quantize import TurboQuantOptimizer

    optimizer = TurboQuantOptimizer(
        model_path=str(model_path),
        output_dir=args.output,
    )
    optimizer.load_model()

    exported = []

    if args.standard:
        print("\n⚙️  Exporting standard FP32 TFLite...")
        path = optimizer.export_tflite_standard()
        exported.append(("standard_fp32", path))
        print(f"   ✅ Saved: {path}")

    if args.fp16:
        print("\n⚙️  Exporting FP16 quantized...")
        path = optimizer.quantize_fp16()
        exported.append(("fp16", path))
        print(f"   ✅ Saved: {path}")

    if args.int8:
        print("\n⚙️  Exporting INT8 quantized (with calibration)...")
        path = optimizer.quantize_int8()
        exported.append(("int8", path))
        print(f"   ✅ Saved: {path}")

    if args.benchmark and exported:
        print("\n📊 Running benchmarks...")
        from ai_model.optimization.benchmark import benchmark_tflite, _print_comparison_table
        results = {}
        for name, path in exported:
            results[name] = benchmark_tflite(path, n_runs=args.benchmark_runs)
        _print_comparison_table(results)

        report_path = Path(args.output) / "benchmark_report.json"
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Benchmark report: {report_path}")

    print("\n" + "=" * 60)
    print("  ✅ Export Complete!")
    print()
    print("  Next steps:")
    print("  1. Copy model_latest.tflite to backend/app/models/")
    print("  2. Copy model_int8.tflite to frontend/assets/ for on-device inference")
    print("  3. Restart backend: python scripts/start_server.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
