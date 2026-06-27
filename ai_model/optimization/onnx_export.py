"""
ONNX model export for the PyTorch hybrid model.

Usage:
    python -m ai_model.optimization.onnx_export \\
        --model ai_model/saved_models/hybrid_torch/model_best.pt \\
        --output ai_model/saved_models/hybrid_model.onnx
"""

import argparse
import logging
import sys
from pathlib import Path

import torch
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("onnx_export")


def export_to_onnx(
    model_path: str | Path,
    output_path: str | Path = "ai_model/saved_models/hybrid_model.onnx",
    opset_version: int = 17,
    dynamic_batch: bool = True,
) -> str:
    """Export a PyTorch hybrid model to ONNX format."""
    model_path = Path(model_path)
    output_path = Path(output_path)

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    device = torch.device("cpu")

    try:
        from ai_model.hybrid_torch.model import HybridTorchModel
        model = HybridTorchModel()
        state = torch.load(str(model_path), map_location=device, weights_only=True)
        model.load_state_dict(state)
        model.eval()
        model.to(device)
    except Exception as exc:
        logger.error("Failed to load model: %s", exc)
        raise

    dummy_input = torch.randn(1, 3, 224, 224, device=device)

    dynamic_axes = None
    if dynamic_batch:
        dynamic_axes = {
            "input": {0: "batch_size"},
            "tread_depths": {0: "batch_size"},
            "health_score": {0: "batch_size"},
            "remaining_life": {0: "batch_size"},
            "wear_probs": {0: "batch_size"},
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)

    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        input_names=["input"],
        output_names=["tread_depths", "health_score", "remaining_life", "wear_probs"],
        dynamic_axes=dynamic_axes,
        opset_version=opset_version,
        export_params=True,
        do_constant_folding=True,
    )

    logger.info("ONNX model exported to: %s", output_path)
    logger.info("  Input shape:  (N, 3, 224, 224)")
    logger.info("  Outputs: tread_depths, health_score, remaining_life, wear_probs")

    return str(output_path)


def verify_onnx_model(onnx_path: str | Path) -> dict:
    """Verify ONNX model with onnxruntime."""
    import onnx
    onnx_path = Path(onnx_path)

    model = onnx.load(str(onnx_path))
    onnx.checker.check_model(model)

    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path))
        input_name = session.get_inputs()[0].name
        dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
        outputs = session.run(None, {input_name: dummy})
        return {
            "valid": True,
            "inputs": [{"name": i.name, "shape": i.shape, "type": i.type} for i in session.get_inputs()],
            "outputs": [{"name": o.name, "shape": o.shape, "type": o.type} for o in session.get_outputs()],
            "output_values": [o.tolist() for o in outputs],
        }
    except ImportError:
        logger.warning("onnxruntime not installed; skipping verification")
        return {"valid": True, "verified": "skipped (onnxruntime not available)"}


def main():
    parser = argparse.ArgumentParser(description="Export hybrid model to ONNX")
    parser.add_argument("--model", default="ai_model/saved_models/hybrid_torch/model_best.pt")
    parser.add_argument("--output", default="ai_model/saved_models/hybrid_model.onnx")
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--verify", action="store_true", default=True)
    args = parser.parse_args()

    path = export_to_onnx(args.model, args.output, opset_version=args.opset)

    if args.verify:
        result = verify_onnx_model(path)
        logger.info("Verification: %s", "PASS" if result.get("valid") else "FAIL")
        if "output_values" in result:
            logger.info("Sample output: %s", result["output_values"][0][:5])


if __name__ == "__main__":
    main()
