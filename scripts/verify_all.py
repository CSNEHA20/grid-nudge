#!/usr/bin/env python3
"""Cross-platform master verification script for complete fresh-clone validation."""

import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


def run_step(desc: str, cmd: list, cwd: Path = ROOT_DIR):
    print(f"\n==========================================")
    print(desc)
    print(f"==========================================")
    subprocess.run(cmd, cwd=str(cwd), check=True, shell=sys.platform.startswith("win"))


def main():
    run_step("Step 1: Prepare Datasets", [sys.executable, "scripts/prepare_data.py"])
    run_step("Step 2: Run Python Test Suite", [sys.executable, "-m", "pytest", "-q"])
    run_step("Step 3: Audit Project Claims", [sys.executable, "scripts/check_claims.py"])
    run_step("Step 4: Check Module Ownership", [sys.executable, "scripts/check_ownership.py"])
    run_step("Step 5: Dashboard Build Verification", ["npm", "run", "build"], cwd=ROOT_DIR / "dashboard")
    print("\n==========================================")
    print("SUCCESS: All GridNudge Verifications Passed!")
    print("==========================================")


if __name__ == "__main__":
    main()
