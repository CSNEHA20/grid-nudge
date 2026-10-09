"""Tests for M4 Planner module.

Validates plan enumeration, outcome prediction (cost, journey confidence, grid value,
battery stress delta, queue wait), monotonicity, and safety risk detection.
"""

import pytest

from gridnudge.contracts import Plan
from gridnudge.perception.station import StationView
from gridnudge.planner import (
    calculate_charging_cost_inr,
    generate_candidate_plans,
    get_tariff_rate_inr,
)


class TestPlanner:
    """Tests for charging plan enumeration and predicted outcomes."""

    @pytest.fixture
    def standard_ev(self):
        """Standard residential EV plugged in at evening peak with overnight dwell."""
        return {
            "user_id": 101,
            "battery_kwh": 40.0,
            "current_soc": 0.30,
            "target_soc": 0.90,
            "charger_kw": 7.4,
            "commute_km": 45.0,
            "base_wh_km": 160.0,
            "hours_until_departure": 12.0,  # Departs at 07:00 next morning
            "has_home_charging": True,
            "location": "home",
        }

    def test_planner_returns_multiple_plans_for_typical_ev(self, standard_ev):
        """Typical EV must receive at least 2 distinct feasible charging plans."""
        plans = generate_candidate_plans(
            ev_context=standard_ev,
            sim_time_iso="2026-10-10T19:00:00+05:30",
            hour_of_day=19.0,
            grid_stress=0.88,
        )
        assert len(plans) >= 2
        types = [p.type for p in plans]
        assert "default" in types
        assert "delay" in types

        for p in plans:
            assert isinstance(p, Plan)
            assert "cost_inr" in p.outcomes
            assert "journey_conf_lb" in p.outcomes
            assert "grid_value" in p.outcomes
            assert "battery_stress_delta" in p.outcomes
            assert "wait_min" in p.outcomes

    def test_delay_plan_cost_savings_and_grid_value(self, standard_ev):
        """Delay plan shifted to night tariff must save money and provide positive grid value."""
        plans = generate_candidate_plans(
            ev_context=standard_ev,
            sim_time_iso="2026-10-10T19:00:00+05:30",
            hour_of_day=19.0,
            grid_stress=0.90,
        )
        default_plan = next(p for p in plans if p.type == "default")
        delay_plan = next(p for p in plans if p.type == "delay")

        # Night rate (6.0 INR/kWh) vs Peak rate (8.5 INR/kWh)
        assert delay_plan.outcomes["cost_inr"] < default_plan.outcomes["cost_inr"]

        # Grid value of shifting out of peak must be positive
        assert delay_plan.outcomes["grid_value"] > 0.0
        assert default_plan.outcomes["grid_value"] < 0.0

    def test_top_up_now_appears_when_confidence_at_risk(self):
        """Low SOC or vulnerable confidence must trigger top_up_now plan."""
        vulnerable_ev = {
            "user_id": 202,
            "battery_kwh": 30.0,
            "current_soc": 0.12,  # Very low SOC
            "target_soc": 0.85,
            "charger_kw": 7.4,
            "commute_km": 60.0,  # Long commute
            "hours_until_departure": 3.0,  # Tight departure window
            "has_home_charging": True,
            "location": "home",
        }
        plans = generate_candidate_plans(
            ev_context=vulnerable_ev,
            sim_time_iso="2026-10-10T18:00:00+05:30",
            hour_of_day=18.0,
        )
        types = [p.type for p in plans]
        assert "top_up_now" in types

    def test_monotone_journey_confidence_under_insufficient_time(self):
        """Delaying charging when departure is early leads to lower journey confidence than default."""
        early_departure_ev = {
            "user_id": 303,
            "battery_kwh": 40.0,
            "current_soc": 0.20,
            "target_soc": 0.90,
            "charger_kw": 7.4,
            "commute_km": 50.0,
            "hours_until_departure": 5.0,  # Departs in 5 hours!
            "has_home_charging": True,
            "location": "home",
        }
        plans = generate_candidate_plans(
            ev_context=early_departure_ev,
            sim_time_iso="2026-10-10T19:00:00+05:30",
            hour_of_day=19.0,
        )
        default_plan = next(p for p in plans if p.type == "default")
        delay_plan = next(p for p in plans if p.type == "delay")

        # Because delay to 23:00 leaves only 1 hour before departure,
        # delay plan cannot deliver required energy -> lower journey confidence!
        assert delay_plan.outcomes["journey_conf_lb"] < default_plan.outcomes["journey_conf_lb"]

    def test_relocate_plan_generated_for_public_station_with_long_queue(self):
        """Public charging user facing heavy queue is offered a relocate plan to alternate station."""
        public_ev = {
            "user_id": 404,
            "battery_kwh": 50.0,
            "current_soc": 0.25,
            "target_soc": 0.80,
            "charger_kw": 50.0,
            "commute_km": 40.0,
            "hours_until_departure": 6.0,
            "has_home_charging": False,
            "location": "station_1",
        }
        station_views = {
            1: StationView(eta_wait_min_q50=35.0, eta_wait_min_q90=55.0, reliability=0.95),
            2: StationView(eta_wait_min_q50=2.0, eta_wait_min_q90=5.0, reliability=0.98),
        }
        plans = generate_candidate_plans(
            ev_context=public_ev,
            sim_time_iso="2026-10-10T14:00:00+05:30",
            hour_of_day=14.0,
            station_views=station_views,
        )
        types = [p.type for p in plans]
        assert "relocate" in types
        relocate_plan = next(p for p in plans if p.type == "relocate")
        assert relocate_plan.where == "station_2"
        assert relocate_plan.outcomes["wait_min"] < 35.0

    def test_tariff_order_rates(self):
        """ToU tariff rates adhere to DERC Delhi structure."""
        assert get_tariff_rate_inr(13.0) == 4.50  # Solar hours
        assert get_tariff_rate_inr(20.0) == 8.50  # Evening peak
        assert get_tariff_rate_inr(2.0) == 6.00  # Night
        assert calculate_charging_cost_inr(start_hour=2.0, duration_hours=4.0, power_kw=7.4) > 0.0
