#!/usr/bin/env python3
"""Cross-platform script to generate / prepare all 7 processed datasets and validate schemas."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = ["grid", "sessions", "stations", "rct", "battery", "ved", "weather"]


def main():
    print("==========================================")
    print("Preparing GridNudge Datasets")
    print("==========================================")
    for s in SCRIPTS:
        script_path = ROOT_DIR / "data" / "scripts" / f"fetch_{s}.py"
        print(f"Running {script_path.relative_to(ROOT_DIR)}...")
        res = subprocess.run([sys.executable, str(script_path)], check=True)

    validate_path = ROOT_DIR / "data" / "scripts" / "validate.py"
    print(f"Validating generated schemas ({validate_path.relative_to(ROOT_DIR)})...")
    subprocess.run([sys.executable, str(validate_path)], check=True)
    print("Dataset preparation complete.")


if __name__ == "__main__":
    main()
