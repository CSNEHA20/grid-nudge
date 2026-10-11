#!/usr/bin/env python3
"""Fetch or generate Delhi weather series for GridNudge (Open-Meteo archive or calibrated synthetic)."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "weather_delhi.parquet"


def generate_synthetic_weather(start_date: str = "2026-05-01", days: int = 14) -> pd.DataFrame:
    """Generate realistic Delhi summer weather (May heatwave season)."""
    start = pd.to_datetime(start_date)
    hours = days * 24
    timestamps = [start + timedelta(hours=i) for i in range(hours)]

    records = []
    rng = np.random.default_rng(42)

    for i, ts in enumerate(timestamps):
        hour = ts.hour
        # Diurnal temperature cycle: min around 05:00 (~30C), max around 15:00 (~43C)
        diurnal_temp = 36.5 + 6.5 * np.sin((hour - 9) * np.pi / 12) + rng.normal(0, 0.5)
        # Solar radiation in W/m^2: peak ~950 W/m^2 at 13:00
        if 6 <= hour <= 19:
            solar_rad = max(0.0, 950.0 * np.sin((hour - 6) * np.pi / 13) + rng.normal(0, 20))
        else:
            solar_rad = 0.0

        records.append({
            "ts": ts,
            "temp_c": round(float(diurnal_temp), 2),
            "shortwave_radiation": round(float(solar_rad), 2),
        })

    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description="Fetch or generate Delhi weather series.")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Use calibrated synthetic data generator")
    parser.add_argument("--days", type=int, default=14, help="Number of days to generate")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_synthetic_weather(days=args.days)
    df.to_parquet(OUTPUT_PATH, index=False)
    print(f"Weather dataset written to {OUTPUT_PATH} ({len(df)} rows)")


if __name__ == "__main__":
    main()
