"""
Run all tests with coverage reporting.
Usage: python scripts/run_tests.py
"""

import subprocess
import sys
from pathlib import Path


def run_tests():
    project_root = Path(__file__).parent.parent
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--no-header",
        "-q",
        f"--rootdir={project_root}",
    ]

    # Try to add coverage if available
    try:
        import coverage
        cmd.extend(["--cov=backend", "--cov=ai_model", "--cov-report=term-missing"])
    except ImportError:
        print("Note: Install pytest-cov for coverage reporting: pip install pytest-cov")

    print("Running Smart Tire Analyzer test suite...")
    print(f"Command: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=project_root)
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
