"""Run the local MLOps lifecycle snapshot for demos and documentation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.services.enterprise_ai_service import EnterpriseAIService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart Tire Analyzer local MLOps pipeline")
    parser.add_argument(
        "--event",
        default="local_mlops_snapshot",
        help="Lifecycle event name to write into training_logs/mlops_events.",
    )
    args = parser.parse_args()

    service = EnterpriseAIService()
    snapshot = service.mlops_snapshot()
    event_path = service.record_mlops_event(args.event, snapshot)

    print(json.dumps({"event_path": str(event_path), "mlops": snapshot}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
