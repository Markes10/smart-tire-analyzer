"""Small CLI to run the deterministic post-processing and print JSON.

Example:
  python scripts/infer_tire_report.py --image ./images/t1.jpg --model-json out.json
"""
import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from ai_model.inference.tire_report import generate_tire_report


def load_model_outputs(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    return json.loads(p.read_text())


def main() -> None:
    p = argparse.ArgumentParser(description="Infer tire report from image and model outputs")
    p.add_argument("--image", required=True, help="Path to input image")
    p.add_argument("--model-json", help="Optional JSON file with model outputs (dict)")
    p.add_argument("--ocr-text", help="Optional OCR raw text to be parsed")
    p.add_argument("--ocr-confidence", help="Optional OCR confidence (float 0-1 or quality string)")
    args = p.parse_args()

    model_outputs = load_model_outputs(args.model_json)
    report = generate_tire_report(
        args.image,
        model_outputs=model_outputs,
        ocr_text=args.ocr_text,
        ocr_confidence=args.ocr_confidence,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
