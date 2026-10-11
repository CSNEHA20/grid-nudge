#!/usr/bin/env python3
"""Fetch or generate Grid-India hourly demand and renewable series for GridNudge."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "grid_series.parquet"


def generate_synthetic_grid_series(start_date: str = "2026-05-01", days: int = 14) -> pd.DataFrame:
    """Generate realistic normalized Delhi grid demand, solar, and wind profiles."""
    start = pd.to_datetime(start_date)
    hours = days * 24
    timestamps = [start + timedelta(hours=i) for i in range(hours)]

    records = []
    rng = np.random.default_rng(42)

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        # Diurnal normalized demand curve with morning dip and pronounced evening peak (20:00-22:00)
        t_rad = (hour / 24.0) * 2.0 * np.pi
        h1 = -np.cos(t_rad - 0.5)
        h2 = 0.35 * -np.cos(2.0 * t_rad - 1.2)
        h3 = 0.15 * -np.cos(3.0 * t_rad)
        demand_raw = (h1 + h2 + h3 + 1.2) / 2.4
        demand_norm = max(0.1, min(0.99, demand_raw + rng.normal(0, 0.02)))

        # Solar profile (normalized in [0, 1], peak at 13:00)
        if 6 <= hour <= 18:
            solar_raw = np.sin((hour - 6) * np.pi / 12) ** 1.5
            solar_norm = max(0.0, min(1.0, solar_raw + rng.normal(0, 0.02)))
        else:
            solar_norm = 0.0

        # Wind profile (moderately noisy, higher at night)
        wind_raw = 0.4 + 0.2 * np.cos(t_rad - 2.5) + rng.normal(0, 0.05)
        wind_norm = max(0.05, min(0.95, wind_raw))

        records.append({
            "ts": ts,
            "demand_norm": round(float(demand_norm), 4),
            "solar_norm": round(float(solar_norm), 4),
            "wind_norm": round(float(wind_norm), 4),
        })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description="Fetch or generate Grid series.")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Use calibrated synthetic data generator")
    parser.add_argument("--days", type=int, default=14, help="Number of days to generate")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_grid_series(days=args.days)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Grid series written to {OUTPUT_PATH} ({len(df)} rows)")


if __name__ == "__main__":
    main()
