#!/usr/bin/env python3
"""Fetch or generate Delhi weather series for GridNudge (Open-Meteo archive or calibrated synthetic)."""

import argparse
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import urllib.request
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("fetch_weather")

ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT_DIR / "data" / "processed" / "weather_delhi.parquet"
META_PATH = ROOT_DIR / "data" / "processed" / "weather_delhi_provenance.json"


def fetch_open_meteo_weather(
    latitude: float = 28.6139,
    longitude: float = 77.2090,
    start_date: str = "2024-05-01",
    end_date: str = "2024-05-14",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Fetch hourly Delhi temperature and irradiance from Open-Meteo Historical Archive API (no key required)."""
    url = (
        f"https://archive-api.open-meteo.com/v1/archive?"
        f"latitude={latitude}&longitude={longitude}&"
        f"start_date={start_date}&end_date={end_date}&"
        f"hourly=temperature_2m,direct_normal_irradiance"
    )
    logger.info("Fetching real weather data from Open-Meteo: %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "GridNudge-DataIngest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    irrads = hourly.get("direct_normal_irradiance", [])

    records = []
    for t_str, temp, irr in zip(times, temps, irrads):
        records.append({
            "ts": pd.to_datetime(t_str),
            "temp_c": round(float(temp), 2) if temp is not None else 35.0,
            "shortwave_radiation": round(float(irr), 2) if irr is not None else 0.0,
        })

    df = pd.DataFrame(records)
    prov = {
        "source": "Open-Meteo Historical Weather API",
        "url": url,
        "latitude": latitude,
        "longitude": longitude,
        "location": "New Delhi, India",
        "start_date": start_date,
        "end_date": end_date,
        "is_synthetic": False,
        "rows": len(df),
        "fetched_at": datetime.now().isoformat(),
    }
    return df, prov


def generate_synthetic_weather(start_date: str = "2026-05-01", days: int = 14) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Generate calibrated synthetic Delhi summer weather (May heatwave season)."""
    start = pd.to_datetime(start_date)
    hours = days * 24
    timestamps = [start + timedelta(hours=i) for i in range(hours)]

    records = []
    rng = np.random.default_rng(42)

    for ts in timestamps:
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

    df = pd.DataFrame(records)
    prov = {
        "source": "Calibrated Synthetic Delhi May Heatwave Generator",
        "location": "New Delhi, India",
        "is_synthetic": True,
        "rows": len(df),
        "generated_at": datetime.now().isoformat(),
    }
    return df, prov


def main():
    parser = argparse.ArgumentParser(description="Fetch or generate Delhi weather series.")
    parser.add_argument("--synthetic", action="store_true", help="Force calibrated synthetic generator")
    parser.add_argument("--days", type=int, default=14, help="Number of days to generate/fetch")
    args = parser.parse_args()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df: pd.DataFrame
    meta: Dict[str, Any]

    if not args.synthetic:
        try:
            df, meta = fetch_open_meteo_weather()
            logger.info("Successfully fetched %d real weather observations from Open-Meteo", len(df))
        except Exception as ex:
            logger.warning("Open-Meteo fetch failed (%s); falling back to calibrated synthetic generator", ex)
            df, meta = generate_synthetic_weather(days=args.days)
    else:
        df, meta = generate_synthetic_weather(days=args.days)
        logger.info("Generated %d synthetic weather observations", len(df))

    df.to_parquet(OUTPUT_PATH, index=False)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    logger.info("Weather dataset written to %s (%d rows)", OUTPUT_PATH, len(df))
    logger.info("Provenance metadata written to %s", META_PATH)


if __name__ == "__main__":
    main()
