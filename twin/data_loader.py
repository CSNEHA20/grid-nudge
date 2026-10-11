"""Data loader module for digital twin grounding datasets.

Loads processed Parquet files from data/processed/ if present;
otherwise falls back gracefully to calibrated synthetic models with audit logging.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"


def load_weather_series(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load hourly Delhi weather data (temperature and solar radiation)."""
    target = path or (PROCESSED_DIR / "weather_delhi.parquet")
    if target.exists():
        try:
            df = pd.read_parquet(target)
            return df
        except Exception as e:
            logger.warning("Failed to load weather data from %s: %s. Using synthetic model.", target, e)
    return None


def load_grid_series(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load normalized Grid-India hourly demand, solar, and wind series."""
    target = path or (PROCESSED_DIR / "grid_series.parquet")
    if target.exists():
        try:
            df = pd.read_parquet(target)
            return df
        except Exception as e:
            logger.warning("Failed to load grid series from %s: %s. Using synthetic model.", target, e)
    return None


def load_sessions_profile(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load EV session empirical arrival hours, dwell durations, and energy profiles."""
    target = path or (PROCESSED_DIR / "sessions_profile.parquet")
    if target.exists():
        try:
            df = pd.read_parquet(target)
            return df
        except Exception as e:
            logger.warning("Failed to load session profile from %s: %s. Using synthetic model.", target, e)
    return None


def load_stations_delhi(path: Optional[Path] = None) -> Optional[pd.DataFrame]:
    """Load Delhi public charging plaza registry."""
    target = path or (PROCESSED_DIR / "stations_delhi.parquet")
    if target.exists():
        try:
            df = pd.read_parquet(target)
            return df
        except Exception as e:
            logger.warning("Failed to load stations dataset from %s: %s. Using synthetic model.", target, e)
    return None


def get_data_provenance() -> Dict[str, str]:
    """Return provenance mapping for each dataset used in the simulation run."""
    return {
        "weather_delhi": "Processed (Open-Meteo / Grounded)" if (PROCESSED_DIR / "weather_delhi.parquet").exists() else "Calibrated Synthetic",
        "grid_series": "Processed (Grid-India / POSOCO)" if (PROCESSED_DIR / "grid_series.parquet").exists() else "Calibrated Synthetic",
        "sessions_profile": "Processed (ACN-Data / Dataverse)" if (PROCESSED_DIR / "sessions_profile.parquet").exists() else "Calibrated Synthetic",
        "stations_delhi": "Processed (BEE / Ministry of Power)" if (PROCESSED_DIR / "stations_delhi.parquet").exists() else "Calibrated Synthetic",
        "tariffs": "DERC Delhi ToU Order (config/tariffs.yaml)",
    }
