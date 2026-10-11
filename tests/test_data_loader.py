"""Unit tests for Stage C data loaders and provenance auditing (M1 / C8).

Validates:
- Real vs synthetic dataset loading
- Graceful fallback when Parquet files are absent
- World provenance metadata reporting
"""

from pathlib import Path
import pytest
import pandas as pd

from twin.data_loader import (
    load_weather_series,
    load_grid_series,
    load_sessions_profile,
    load_stations_delhi,
    load_rct_nudge_response,
    load_battery_aging_reference,
    load_ved_trip_energy,
)
from twin.world import World


def test_data_loaders_load_processed_parquets_if_present():
    """Loaders must return DataFrames with expected schemas when processed files exist."""
    weather = load_weather_series()
    if weather is not None:
        assert isinstance(weather, pd.DataFrame)
        assert "temp_c" in weather.columns or "temperature_c" in weather.columns

    grid = load_grid_series()
    if grid is not None:
        assert isinstance(grid, pd.DataFrame)
        assert "demand_norm" in grid.columns

    sessions = load_sessions_profile()
    if sessions is not None:
        assert isinstance(sessions, pd.DataFrame)
        assert "kwh" in sessions.columns

    stations = load_stations_delhi()
    if stations is not None:
        assert isinstance(stations, pd.DataFrame)
        assert "station_id" in stations.columns

    rct = load_rct_nudge_response()
    if rct is not None:
        assert isinstance(rct, pd.DataFrame)
        assert "treatment_group" in rct.columns
        assert "adopted_shift" in rct.columns

    battery = load_battery_aging_reference()
    if battery is not None:
        assert isinstance(battery, pd.DataFrame)
        assert "stress_index" in battery.columns

    ved = load_ved_trip_energy()
    if ved is not None:
        assert isinstance(ved, pd.DataFrame)
        assert "wh_per_km" in ved.columns


def test_data_loaders_fallback_gracefully_when_file_missing():
    """Loaders must return None and log warning when given non-existent paths."""
    missing_path = Path("/nonexistent/file.parquet")
    assert load_weather_series(missing_path) is None
    assert load_grid_series(missing_path) is None
    assert load_sessions_profile(missing_path) is None
    assert load_stations_delhi(missing_path) is None
    assert load_rct_nudge_response(missing_path) is None
    assert load_battery_aging_reference(missing_path) is None
    assert load_ved_trip_energy(missing_path) is None


def test_world_provenance_metadata():
    """World instance must report structured provenance reflecting data sources."""
    world = World(seed=42, n_users=20)
    prov = world.get_provenance()
    assert isinstance(prov, dict)
    assert "weather_delhi" in prov
    assert "grid_series" in prov
    assert "stations_delhi" in prov
    assert "tariffs" in prov
    assert "sessions_profile" in prov
    assert "rct_nudge_response" in prov
    assert "battery_aging_reference" in prov
    assert "ved_trip_energy" in prov

