#!/usr/bin/env python3
"""authoritative schema and data validation for GridNudge M1 datasets and tariffs.

Validates the four processed Parquet files under data/processed/ and config/tariffs.yaml
against schemas defined in GRIDNUDGE_MASTER_PLAN.md.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

# Resolve repository root: data/scripts/validate.py -> parents[2] is root
ROOT_DIR = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
TARIFFS_PATH = ROOT_DIR / "config" / "tariffs.yaml"


class ValidationError(Exception):
    """Raised when dataset or configuration schema validation fails."""


def validate_dataframe_columns(
    df: pd.DataFrame,
    required_cols: list[str],
    dataset_name: str,
) -> None:
    """Ensure all required columns exist in the DataFrame."""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValidationError(
            f"[{dataset_name}] Missing required column(s): {', '.join(missing)}"
        )


def validate_no_nulls(
    df: pd.DataFrame,
    columns: list[str],
    dataset_name: str,
) -> None:
    """Ensure specified columns have no null / NaN values."""
    for col in columns:
        null_count = df[col].isna().sum()
        if null_count > 0:
            raise ValidationError(
                f"[{dataset_name}] Column '{col}' contains {null_count} null/NaN value(s)"
            )


def validate_datetime_column(
    df: pd.DataFrame,
    col: str,
    dataset_name: str,
) -> None:
    """Verify that a column contains valid datetime values."""
    if not pd.api.types.is_datetime64_any_dtype(df[col]):
        try:
            pd.to_datetime(df[col], errors="raise")
        except Exception as exc:
            raise ValidationError(
                f"[{dataset_name}] Column '{col}' is not datetime-compatible: {exc}"
            ) from exc


def validate_grid_series(path: Path) -> None:
    """Validate data/processed/grid_series.parquet."""
    name = "grid_series.parquet"
    if not path.exists():
        raise ValidationError(f"[{name}] File not found at {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValidationError(f"[{name}] Dataset is empty")

    required = ["ts", "demand_norm", "solar_norm", "wind_norm"]
    validate_dataframe_columns(df, required, name)
    validate_no_nulls(df, required, name)
    validate_datetime_column(df, "ts", name)

    numeric_cols = ["demand_norm", "solar_norm", "wind_norm"]
    for col in numeric_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValidationError(f"[{name}] Column '{col}' must be numeric")
        min_val = float(df[col].min())
        max_val = float(df[col].max())
        if min_val < -1e-6 or max_val > 1.0 + 1e-6:
            raise ValidationError(
                f"[{name}] Column '{col}' values must be in [0, 1], found range [{min_val}, {max_val}]"
            )


def validate_weather_delhi(path: Path) -> None:
    """Validate data/processed/weather_delhi.parquet."""
    name = "weather_delhi.parquet"
    if not path.exists():
        raise ValidationError(f"[{name}] File not found at {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValidationError(f"[{name}] Dataset is empty")

    required = ["ts", "temp_c", "shortwave_radiation"]
    validate_dataframe_columns(df, required, name)
    validate_no_nulls(df, required, name)
    validate_datetime_column(df, "ts", name)

    for col in ["temp_c", "shortwave_radiation"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValidationError(f"[{name}] Column '{col}' must be numeric")

    rad_min = float(df["shortwave_radiation"].min())
    if rad_min < -1e-6:
        raise ValidationError(
            f"[{name}] Column 'shortwave_radiation' cannot be negative, min value is {rad_min}"
        )


def validate_sessions_profile(path: Path) -> None:
    """Validate data/processed/sessions_profile.parquet."""
    name = "sessions_profile.parquet"
    if not path.exists():
        raise ValidationError(f"[{name}] File not found at {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValidationError(f"[{name}] Dataset is empty")

    required = ["arrival_hour", "dwell_hours", "kwh"]
    validate_dataframe_columns(df, required, name)
    validate_no_nulls(df, required, name)

    if not pd.api.types.is_integer_dtype(df["arrival_hour"]) and not pd.api.types.is_float_dtype(df["arrival_hour"]):
        raise ValidationError(f"[{name}] Column 'arrival_hour' must be numeric/integer-compatible")

    if ((df["arrival_hour"] % 1) != 0).any():
        raise ValidationError(f"[{name}] Column 'arrival_hour' contains non-integer values")

    min_hour = int(df["arrival_hour"].min())
    max_hour = int(df["arrival_hour"].max())
    if min_hour < 0 or max_hour > 23:
        raise ValidationError(
            f"[{name}] Column 'arrival_hour' must be in [0, 23], found range [{min_hour}, {max_hour}]"
        )

    for col in ["dwell_hours", "kwh"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValidationError(f"[{name}] Column '{col}' must be numeric")
        min_val = float(df[col].min())
        if min_val < -1e-6:
            raise ValidationError(
                f"[{name}] Column '{col}' cannot be negative, found min {min_val}"
            )


def validate_stations_delhi(path: Path) -> None:
    """Validate data/processed/stations_delhi.parquet."""
    name = "stations_delhi.parquet"
    if not path.exists():
        raise ValidationError(f"[{name}] File not found at {path}")

    df = pd.read_parquet(path)
    if df.empty:
        raise ValidationError(f"[{name}] Dataset is empty")

    required = ["station_id", "lat", "lon", "charger_type", "kw", "connectors"]
    validate_dataframe_columns(df, required, name)
    validate_no_nulls(df, required, name)

    # Station IDs and charger types must be non-empty strings
    if (df["station_id"].astype(str).str.strip() == "").any():
        raise ValidationError(f"[{name}] Column 'station_id' contains empty string(s)")
    if (df["charger_type"].astype(str).str.strip() == "").any():
        raise ValidationError(f"[{name}] Column 'charger_type' contains empty string(s)")

    # Geographic coordinates
    for col in ["lat", "lon"]:
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValidationError(f"[{name}] Column '{col}' must be numeric")

    lat_min, lat_max = float(df["lat"].min()), float(df["lat"].max())
    if lat_min < -90.0 or lat_max > 90.0:
        raise ValidationError(
            f"[{name}] Column 'lat' out of valid range [-90, 90]: [{lat_min}, {lat_max}]"
        )

    lon_min, lon_max = float(df["lon"].min()), float(df["lon"].max())
    if lon_min < -180.0 or lon_max > 180.0:
        raise ValidationError(
            f"[{name}] Column 'lon' out of valid range [-180, 180]: [{lon_min}, {lon_max}]"
        )

    # Power and connectors must be positive
    if not pd.api.types.is_numeric_dtype(df["kw"]):
        raise ValidationError(f"[{name}] Column 'kw' must be numeric")
    kw_min = float(df["kw"].min())
    if kw_min <= 0.0:
        raise ValidationError(f"[{name}] Column 'kw' must be strictly positive, min is {kw_min}")

    if not pd.api.types.is_integer_dtype(df["connectors"]) and not pd.api.types.is_float_dtype(df["connectors"]):
        raise ValidationError(f"[{name}] Column 'connectors' must be integer-compatible")
    if ((df["connectors"] % 1) != 0).any():
        raise ValidationError(f"[{name}] Column 'connectors' contains non-integer values")

    conn_min = int(df["connectors"].min())
    if conn_min < 1:
        raise ValidationError(
            f"[{name}] Column 'connectors' must be at least 1, min is {conn_min}"
        )


def validate_tariffs_yaml(path: Path) -> None:
    """Validate config/tariffs.yaml structure and values."""
    name = "tariffs.yaml"
    if not path.exists():
        raise ValidationError(f"[{name}] File not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValidationError(f"[{name}] Top-level content must be a mapping (dict)")

    if "currency" not in data or not isinstance(data["currency"], str):
        raise ValidationError(f"[{name}] Missing or invalid 'currency' string field")

    slots = data.get("slots")
    if not isinstance(slots, dict) or not slots:
        raise ValidationError(f"[{name}] Missing or invalid non-empty 'slots' dictionary")

    required_slot_fields = ["start_time", "end_time", "rate_inr_kwh"]
    for slot_key, slot_val in slots.items():
        if not isinstance(slot_val, dict):
            raise ValidationError(f"[{name}] Slot '{slot_key}' must be a mapping (dict)")

        for field in required_slot_fields:
            if field not in slot_val:
                raise ValidationError(
                    f"[{name}] Slot '{slot_key}' missing required field '{field}'"
                )

        rate = slot_val["rate_inr_kwh"]
        if not isinstance(rate, (int, float)) or rate < 0:
            raise ValidationError(
                f"[{name}] Slot '{slot_key}' 'rate_inr_kwh' must be non-negative numeric, got {rate}"
            )

        # Basic time format check (HH:MM)
        for t_field in ["start_time", "end_time"]:
            t_val = str(slot_val[t_field]).strip()
            parts = t_val.split(":")
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ValidationError(
                    f"[{name}] Slot '{slot_key}' '{t_field}' must be HH:MM format, got '{t_val}'"
                )

    if "demand_charge_kw_month" in data:
        demand = data["demand_charge_kw_month"]
        if not isinstance(demand, (int, float)) or demand < 0:
            raise ValidationError(
                f"[{name}] 'demand_charge_kw_month' must be non-negative numeric, got {demand}"
            )


def validate_all(
    processed_dir: Path = PROCESSED_DIR,
    tariffs_path: Path = TARIFFS_PATH,
) -> list[str]:
    """Run all dataset and config validations.

    Returns a list of error messages.
    """
    errors: list[str] = []

    validators = [
        ("grid_series.parquet", lambda: validate_grid_series(processed_dir / "grid_series.parquet")),
        ("weather_delhi.parquet", lambda: validate_weather_delhi(processed_dir / "weather_delhi.parquet")),
        ("sessions_profile.parquet", lambda: validate_sessions_profile(processed_dir / "sessions_profile.parquet")),
        ("stations_delhi.parquet", lambda: validate_stations_delhi(processed_dir / "stations_delhi.parquet")),
        ("tariffs.yaml", lambda: validate_tariffs_yaml(tariffs_path)),
    ]

    for label, fn in validators:
        try:
            fn()
            print(f"  [PASS] {label}")
        except ValidationError as err:
            print(f"  [FAIL] {label}: {err}")
            errors.append(str(err))
        except Exception as exc:
            msg = f"Unexpected error validating {label}: {exc}"
            print(f"  [FAIL] {label}: {msg}")
            errors.append(msg)

    return errors


def main() -> int:
    """CLI entrypoint for dataset and configuration validation."""
    print("========================================")
    print("GridNudge M1 Dataset & Config Validation")
    print("========================================")

    errors = validate_all()

    print("----------------------------------------")
    if errors:
        print(f"Validation FAILED with {len(errors)} error(s):")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Validation SUCCESS: All datasets and configurations passed schema checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
