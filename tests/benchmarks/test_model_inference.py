"""
AI model inference benchmarks.
Measures latency for the hybrid PyTorch model on CPU.

Run: python -m tests.benchmarks.test_model_inference
"""

import time
import numpy as np
import torch
from pathlib import Path


def benchmark_torch_inference(n_runs: int = 100):
    """Measure PyTorch model inference latency."""
    device = torch.device("cpu")
    dummy_input = torch.randn(1, 3, 224, 224, device=device)

    try:
        from ai_model.hybrid_torch.model import HybridTorchModel
        model = HybridTorchModel()
        model.eval()
        model.to(device)

        # Warmup
        for _ in range(10):
            _ = model(dummy_input)

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        latencies = []
        for _ in range(n_runs):
            start = time.perf_counter()
            _ = model(dummy_input)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            latencies.append((time.perf_counter() - start) * 1000)

        latencies = np.array(latencies)
        print(f"\n=== PyTorch Hybrid Model Benchmark ({n_runs} runs) ===")
        print(f"  Device: {device}")
        print(f"  Mean:     {latencies.mean():.2f} ms")
        print(f"  Median:   {np.median(latencies):.2f} ms")
        print(f"  P90:      {np.percentile(latencies, 90):.2f} ms")
        print(f"  P99:      {np.percentile(latencies, 99):.2f} ms")
        print(f"  Min:      {latencies.min():.2f} ms")
        print(f"  Max:      {latencies.max():.2f} ms")
        print(f"  Std:      {latencies.std():.2f} ms")
        return latencies
    except ImportError as e:
        print(f"Model import failed: {e}")
        print("Skipping model benchmark (model may not be built)")


def benchmark_cpu_preprocessing(n_runs: int = 100):
    """Benchmark image preprocessing pipeline."""
    import cv2
    import numpy as np

    dummy_image = np.random.randint(0, 255, (1920, 1080, 3), dtype=np.uint8)

    def preprocess(img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.Laplacian(gray, cv2.CV_64F).var()
        resized = cv2.resize(img, (224, 224))
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY))
        normalized = enhanced.astype(np.float32) / 255.0
        return normalized, blur

    # Warmup
    for _ in range(10):
        _ = preprocess(dummy_image)

    latencies = []
    for _ in range(n_runs):
        start = time.perf_counter()
        _ = preprocess(dummy_image)
        latencies.append((time.perf_counter() - start) * 1000)

    latencies = np.array(latencies)
    print(f"\n=== CPU Preprocessing Benchmark ({n_runs} runs) ===")
    print(f"  Mean:     {latencies.mean():.2f} ms")
    print(f"  Median:   {np.median(latencies):.2f} ms")
    print(f"  P90:      {np.percentile(latencies, 90):.2f} ms")
    print(f"  P99:      {np.percentile(latencies, 99):.2f} ms")
    print(f"  Min:      {latencies.min():.2f} ms")
    print(f"  Max:      {latencies.max():.2f} ms")


if __name__ == "__main__":
    benchmark_torch_inference(50)
    benchmark_cpu_preprocessing(50)
