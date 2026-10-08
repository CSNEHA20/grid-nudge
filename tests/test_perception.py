"""Tests for M3 Perception Engines: Journey, Battery, Station, Grid, and Flexibility.

Validates physics models, monotonicity invariants, Erlang-C queue limits,
thermal sensitivity, calibration, and Pydantic contract compliance.
"""

import time
import numpy as np

from gridnudge.contracts import BatteryView, GridView, Journey, StationView
from gridnudge.perception.battery import (
    compute_battery_stress_score,
    estimate_soh_delta_range,
    evaluate_battery_view,
)
from gridnudge.perception.flexibility import (
    compute_ev_shiftable_kwh,
    estimate_fleet_flexibility,
)
from gridnudge.perception.grid import (
    evaluate_grid_view,
    identify_green_charging_window,
)
from gridnudge.perception.journey import (
    JourneyCalibrator,
    batch_estimate_journey_confidence,
    estimate_journey_confidence,
)
from gridnudge.perception.station import (
    erlang_c_probabilities,
    estimate_station_wait,
)


class TestJourneyPerception:
    """Tests for Journey Confidence, thermal sensitivity, and calibration."""

    def test_journey_contract_compliance(self):
        """Verify Journey returns valid Pydantic model with strict constraints."""
        journey = estimate_journey_confidence(
            departure_soc=0.85,
            battery_kwh=40.0,
            distance_km=45.0,
        )
        assert isinstance(journey, Journey)
        assert 0.0 <= journey.p_arrive_above_reserve <= 1.0
        assert 0.0 <= journey.arrival_soc_q10 <= 1.0
        assert 0.0 <= journey.arrival_soc_q50 <= 1.0
        assert 0.0 <= journey.arrival_soc_q90 <= 1.0
        assert journey.arrival_soc_q10 <= journey.arrival_soc_q50 <= journey.arrival_soc_q90

    def test_journey_monotonicity(self):
        """Monotonicity invariant: higher departure SOC must yield non-decreasing confidence."""
        soc_levels = [0.20, 0.40, 0.60, 0.80, 0.95]
        confidences = []
        for soc in soc_levels:
            res = estimate_journey_confidence(
                departure_soc=soc,
                battery_kwh=35.0,
                distance_km=50.0,
                seed=123,
            )
            confidences.append(res.p_arrive_above_reserve)

        for i in range(len(confidences) - 1):
            assert confidences[i] <= confidences[i + 1] + 1e-4

    def test_journey_hot_day_energy_impact(self):
        """Thermal sensitivity: 45°C heatwave increases HVAC load and lowers arrival SOC vs 22°C."""
        mild = estimate_journey_confidence(
            departure_soc=0.70,
            battery_kwh=40.0,
            distance_km=60.0,
            ambient_temp_c=22.0,
            seed=42,
        )
        hot = estimate_journey_confidence(
            departure_soc=0.70,
            battery_kwh=40.0,
            distance_km=60.0,
            ambient_temp_c=45.0,
            seed=42,
        )
        assert hot.arrival_soc_q50 < mild.arrival_soc_q50
        assert hot.p_arrive_above_reserve <= mild.p_arrive_above_reserve

    def test_journey_calibrator(self):
        """Calibrator should map raw values monotonically and fit empirical observations."""
        calibrator = JourneyCalibrator()
        # Test default anchors
        assert calibrator.calibrate(0.0) == 0.0
        assert calibrator.calibrate(1.0) == 1.0
        assert calibrator.calibrate(0.5) > 0.0

        # Fit on synthetic pairs
        preds = np.linspace(0.1, 0.9, 20)
        labels = (preds > 0.45).astype(float)
        calibrator.fit(preds, labels)
        c_low = calibrator.calibrate(0.2)
        c_high = calibrator.calibrate(0.8)
        assert c_low <= c_high

    def test_journey_batch_performance(self):
        """Batch performance: 500 EVs must evaluate in well under 1000 milliseconds."""
        items = [
            {
                "user_id": i,
                "departure_soc": 0.5 + (i % 5) * 0.1,
                "battery_kwh": 30.0 + (i % 3) * 15.0,
                "distance_km": 20.0 + (i % 8) * 10.0,
            }
            for i in range(500)
        ]
        start = time.perf_counter()
        results = batch_estimate_journey_confidence(items, n_draws=250)
        duration_ms = (time.perf_counter() - start) * 1000.0

        assert len(results) == 500
        assert duration_ms < 1000.0  # Runs in ~250ms on standard CPU


class TestBatteryPerception:
    """Tests for battery stress scoring and relative SOH delta interval modeling."""

    def test_battery_view_contract_compliance(self):
        """Ensure BatteryView matches Pydantic contract and relative delta rule."""
        view = evaluate_battery_view(
            soc=0.85,
            battery_kwh=40.0,
            charging_kw=50.0,
            ambient_temp_c=38.0,
            hours_at_high_soc=4.0,
            plan_type="delay",
            delay_hours=3.5,
        )
        assert isinstance(view, BatteryView)
        assert 0.0 <= view.stress_score <= 1.0
        assert isinstance(view.soh_delta_range_pct, tuple)
        assert len(view.soh_delta_range_pct) == 2
        assert view.soh_delta_range_pct[0] <= view.soh_delta_range_pct[1]

    def test_battery_stress_score_drivers(self):
        """High C-rate, high SOC, and high ambient temperature increase stress score."""
        low_stress = compute_battery_stress_score(
            soc=0.40,
            charging_kw=3.3,
            battery_kwh=50.0,
            ambient_temp_c=25.0,
        )
        high_stress = compute_battery_stress_score(
            soc=0.95,
            charging_kw=60.0,
            battery_kwh=30.0,
            ambient_temp_c=44.0,
            hours_at_high_soc=6.0,
        )
        assert high_stress > low_stress

    def test_soh_delta_relative_benefit(self):
        """Delay plan at cooler hours offers positive relative SOH degradation benefit."""
        delta_range = estimate_soh_delta_range(
            plan_type="delay",
            delay_hours=4.0,
            temp_drop_c=5.0,
        )
        # Expected positive benefit (less degradation)
        assert delta_range[1] > 0.0


class TestStationPerception:
    """Tests for Erlang-C queue wait and station reliability modeling."""

    def test_station_view_contract_compliance(self):
        """Validate StationView structure and bounds."""
        view = estimate_station_wait(
            station_id=1,
            arrival_rate_per_hour=6.0,
            avg_dwell_min=30.0,
            connectors=6,
        )
        assert isinstance(view, StationView)
        assert view.eta_wait_min_q50 >= 0.0
        assert view.eta_wait_min_q90 >= view.eta_wait_min_q50
        assert 0.0 <= view.reliability <= 1.0

    def test_erlang_c_light_vs_heavy_traffic(self):
        """Light traffic has near-zero queue wait; heavy traffic causes measurable wait."""
        # Light: 2 cars/hr on 6 connectors with 30 min service
        p_light, wait_light = erlang_c_probabilities(lam_per_min=2.0 / 60.0, mu_per_min=1.0 / 30.0, c=6)
        assert wait_light < 0.1

        # Heavy: 11 cars/hr on 6 connectors
        p_heavy, wait_heavy = erlang_c_probabilities(lam_per_min=11.0 / 60.0, mu_per_min=1.0 / 30.0, c=6)
        assert wait_heavy > wait_light

    def test_station_offline_outage(self):
        """Offline station returns 0 reliability and long cap wait times."""
        view = estimate_station_wait(
            station_id=2,
            arrival_rate_per_hour=5.0,
            connectors=6,
            is_offline=True,
        )
        assert view.reliability == 0.0
        assert view.eta_wait_min_q50 >= 90.0


class TestGridAndFlexibilityPerception:
    """Tests for grid stress profile, green window, and fleet flexibility envelope."""

    def test_grid_view_contract_compliance(self):
        """Validate GridView contract and diurnal profile."""
        grid_view = evaluate_grid_view(
            feeder_load_mw=9.0,
            feeder_capacity_mw=12.0,
            hour_of_day=19.5,
        )
        assert isinstance(grid_view, GridView)
        assert grid_view.stress_q50 > 0.0
        assert grid_view.stress_q90 >= grid_view.stress_q50
        assert grid_view.green_window_start is not None
        assert grid_view.green_window_end is not None

    def test_green_charging_window_hours(self):
        """Green charging window reflects midday solar generation."""
        start_str, end_str = identify_green_charging_window()
        assert start_str == "10:30"
        assert end_str == "15:30"

    def test_ev_shiftable_kwh(self):
        """EV shiftable kWh respects energy needed, charger limits, and departure deadline."""
        # 40kWh battery, from 20% to 90% SOC = 28 kWh needed. 7.4 kW charger.
        # Departure in 10 hours, 3-hour peak window.
        shiftable = compute_ev_shiftable_kwh(
            current_soc=0.20,
            target_soc=0.90,
            battery_kwh=40.0,
            charger_kw=7.4,
            hours_until_departure=10.0,
            peak_window_hours_remaining=3.0,
        )
        # In 3-hour peak, default draw is 3 * 7.4 = 22.2 kWh.
        # Outside peak, 7 hours available = 7 * 7.4 = 51.8 kWh.
        # So shiftable is min(22.2, 51.8) = 22.2 kWh.
        assert shiftable == 22.2

    def test_fleet_flexibility_monte_carlo(self):
        """Fleet flexibility simulation produces labeled quantiles."""
        evs = [
            {
                "current_soc": 0.25,
                "target_soc": 0.90,
                "battery_kwh": 40.0,
                "charger_kw": 7.4,
                "hours_until_departure": 9.0,
                "adoption_prob": 0.40,
            }
            for _ in range(50)
        ]
        result = estimate_fleet_flexibility(evs, n_draws=300)
        assert result["label"] == "Simulation"
        assert result["eligible_ev_count"] == 50
        assert result["shiftable_mw_q10"] <= result["shiftable_mw_q50"] <= result["shiftable_mw_q90"]
        assert result["total_potential_mwh"] > 0.0
