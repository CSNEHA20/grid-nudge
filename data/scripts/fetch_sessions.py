#!/usr/bin/env python3
"""Fetch or generate EV charging session profile dataset for GridNudge."""

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "sessions_profile.parquet"


def generate_synthetic_sessions(n_sessions: int = 5000) -> pd.DataFrame:
    """Generate realistic session arrival hours, dwell times, and energy demands."""
    rng = np.random.default_rng(42)

    # Bimodal arrival distribution: morning commute (8-10 AM) and evening return (17-20 PM)
    p_evening = 0.65
    is_evening = rng.random(n_sessions) < p_evening

    morning_arrivals = rng.normal(8.5, 1.2, n_sessions).astype(int)
    evening_arrivals = rng.normal(18.5, 1.5, n_sessions).astype(int)

    arrival_hours = np.where(is_evening, evening_arrivals, morning_arrivals)
    arrival_hours = np.clip(arrival_hours, 0, 23)

    # Dwell hours: overnight dwell (8-12 hours) vs workday dwell (3-8 hours)
    dwell_hours = np.where(is_evening, rng.uniform(8.0, 14.0, n_sessions), rng.uniform(2.5, 8.0, n_sessions))

    # Energy delivered (kWh): typically 12 to 35 kWh for daily commutes
    kwh = rng.gamma(shape=4.0, scale=4.5, size=n_sessions)
    kwh = np.clip(kwh, 3.0, 58.0)

    df = pd.DataFrame({
        "arrival_hour": arrival_hours.astype(int),
        "dwell_hours": np.round(dwell_hours, 2),
        "kwh": np.round(kwh, 2),
    })
    return df


def main():
    parser = argparse.ArgumentParser(description="Fetch or generate EV session profiles.")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Use calibrated synthetic data generator")
    parser.add_argument("--n-sessions", type=int, default=5000, help="Number of sessions")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_sessions(n_sessions=args.n_sessions)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Session profile written to {OUTPUT_PATH} ({len(df)} rows)")


if __name__ == "__main__":
    main()
