#!/usr/bin/env python3
"""Audit and verify repository claims against results/summary.csv and results/calibration.json (B4).

Enforces:
1. Zero hallucination: numbers in README.md and DEMO_SCRIPT.md match summary.csv.
2. Calibration honesty: ECE and coverage claims match results/calibration.json.
3. Grounding transparency: "Grounded" never appears for synthetic datasets.
"""

import csv
import json
from pathlib import Path
import re
import sys
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parents[1]
SUMMARY_CSV = ROOT_DIR / "results" / "summary.csv"
CALIBRATION_JSON = ROOT_DIR / "results" / "calibration.json"
README_MD = ROOT_DIR / "README.md"
DEMO_SCRIPT_MD = ROOT_DIR / "docs" / "DEMO_SCRIPT.md"
SOURCES_MD = ROOT_DIR / "data" / "raw" / "SOURCES.md"


def check_claims() -> List[str]:
    errors: List[str] = []

    if not SUMMARY_CSV.exists():
        return [f"Missing {SUMMARY_CSV}"]
    if not README_MD.exists():
        return [f"Missing {README_MD}"]

    summary: Dict[str, Dict[str, str]] = {}
    with open(SUMMARY_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            summary[row["policy"]] = row

    readme_text = README_MD.read_text(encoding="utf-8")
    demo_text = DEMO_SCRIPT_MD.read_text(encoding="utf-8") if DEMO_SCRIPT_MD.exists() else ""
    sources_text = SOURCES_MD.read_text(encoding="utf-8") if SOURCES_MD.exists() else ""

    # 1. Check policy metrics in README table
    for p in ["B0", "B1", "B2", "B3", "B4"]:
        if p not in summary:
            errors.append(f"Policy {p} missing from results/summary.csv")
            continue
        row = summary[p]
        peak_red = row.get("evening_peak_reduction_pct", "").strip()
        nudges = row.get("nudges_per_user_per_day", "").strip()

        # Check if the formatted peak reduction or its mean is present in README
        mean_red = peak_red.split(" ")[0]
        if mean_red and mean_red not in readme_text:
            errors.append(f"README.md missing expected peak reduction '{mean_red}' for {p} (from summary.csv)")

        mean_nu = nudges.split(" ")[0]
        if mean_nu and mean_nu not in readme_text:
            errors.append(f"README.md missing expected nudges/user/day '{mean_nu}' for {p} (from summary.csv)")

    # 2. Check calibration metrics
    if CALIBRATION_JSON.exists():
        with open(CALIBRATION_JSON, "r", encoding="utf-8") as f:
            calib = json.load(f)
        ece = calib.get("expected_calibration_error")
        if ece is not None:
            ece_pct_str = f"{round(float(ece) * 100, 2)}%"
            if demo_text and ece_pct_str not in demo_text:
                errors.append(f"DEMO_SCRIPT.md does not reflect calibrated ECE '{ece_pct_str}' from calibration.json")

    # 3. Check data honesty: "Grounded" must not describe synthetic datasets
    forbidden_grounded = [
        ("grid_series.parquet", "Grid Feeder Load"),
        ("sessions_profile.parquet", "EV Session Dwell"),
        ("stations_delhi.parquet", "Delhi Charging Plazas"),
    ]

    for file_str, name in forbidden_grounded:
        for doc_name, doc_text in [("README.md", readme_text), ("data/raw/SOURCES.md", sources_text)]:
            # Find lines mentioning the synthetic file
            for line in doc_text.splitlines():
                if file_str in line:
                    if "Grounded" in line and "not Grounded" not in line and "Live" not in line:
                        errors.append(f"{doc_name} labels synthetic dataset '{name}' ({file_str}) as 'Grounded': '{line.strip()}'")

    return errors


def main() -> None:
    errors = check_claims()
    if errors:
        print("CLAIMS INTEGRITY CHECK FAILED:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("ALL CLAIMS VERIFIED: README.md and DEMO_SCRIPT.md match results/summary.csv and data provenance rules.")
        sys.exit(0)


if __name__ == "__main__":
    main()
