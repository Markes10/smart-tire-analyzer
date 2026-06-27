"""
Profile the inference pipeline to identify bottlenecks.

Usage:
    python scripts/profile_inference.py
    python scripts/profile_inference.py --profile  # with cProfile
"""

import argparse
import cProfile
import pstats
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from PIL import Image


def run_inference_pipeline():
    """Run the full inference pipeline with synthetic data."""
    from app.services.inference_service import InferenceService

    svc = InferenceService()
    svc._load_model()

    dummy_image = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8).astype(np.float32)

    for i in range(10):
        result = svc._predict_sync(dummy_image)
        print(f"Run {i+1}: health={result.get('health_score', 'N/A')}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", action="store_true", help="Run with cProfile")
    args = parser.parse_args()

    if args.profile:
        profiler = cProfile.Profile()
        profiler.enable()
        run_inference_pipeline()
        profiler.disable()

        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s).sort_stats("cumtime")
        stats.print_stats(30)
        print(s.getvalue())
    else:
        run_inference_pipeline()


if __name__ == "__main__":
    main()
