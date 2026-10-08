#!/usr/bin/env python3
"""Generate schema-valid hand-authored fixtures for GridNudge dashboard and testing.

Produces:
- fixtures/decisions.sample.json (veto, silence, and normal nudge)
- fixtures/metrics.timeline.json (two load curves under heatwave peak)
- fixtures/evaluation.summary.json (baselines table with CI)
- fixtures/calibration.json (reliability diagram data)
- fixtures/flexibility.json (forecast flexibility bands)
"""

import json
from pathlib import Path
from gridnudge.contracts import (
    Allocation,
    BatteryView,
    DecisionRecord,
    GridView,
    Journey,
    Language,
    Outcome,
    Persuasion,
    Plan,
    Safety,
    StationView,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def make_decisions_sample() -> list[dict]:
    # 1. Normal Nudge Case
    nudge_record = DecisionRecord(
        decision_id="d_001_nudge_cost",
        run_id="run_20261010_eval_01",
        sim_time="2026-10-10T18:45:00+05:30",
        user_id="user_delhi_0412",
        ev={
            "model": "Tata Nexon EV Max",
            "battery_kwh": 40.5,
            "current_soc": 0.38,
            "target_soc": 0.90,
            "max_ac_kw": 7.2,
            "plugged_in": True,
            "connector_type": "Type 2",
            "location": "home",
        },
        journey=Journey(
            p_arrive_above_reserve=0.94,
            arrival_soc_q10=0.22,
            arrival_soc_q50=0.36,
            arrival_soc_q90=0.48,
            reserve_soc=0.10,
        ),
        battery=BatteryView(
            stress_score=0.28,
            soh_delta_range_pct=(-0.015, 0.040),
        ),
        station=StationView(
            eta_wait_min_q50=0.0,
            eta_wait_min_q90=0.0,
            reliability=0.99,
        ),
        grid=GridView(
            stress_q50=0.88,
            stress_q90=0.95,
            green_window_start="2026-10-10T22:30:00+05:30",
            green_window_end="2026-10-11T05:30:00+05:30",
        ),
        plans=[
            Plan(
                plan_id="plan_default_01",
                type="default",
                start="2026-10-10T18:45:00+05:30",
                kw=7.2,
                where="home",
                outcomes={
                    "cost_inr": 175.5,
                    "journey_conf_lb": 0.98,
                    "grid_value": -0.85,
                    "battery_stress_delta": 0.12,
                    "wait_min": 0.0,
                },
            ),
            Plan(
                plan_id="plan_delay_01",
                type="delay",
                start="2026-10-10T22:30:00+05:30",
                kw=7.2,
                where="home",
                outcomes={
                    "cost_inr": 124.2,
                    "journey_conf_lb": 0.94,
                    "grid_value": 1.45,
                    "battery_stress_delta": -0.05,
                    "wait_min": 0.0,
                },
            ),
        ],
        safety=Safety(
            invariants_ok=True,
            cedar="ALLOW",
            vetoed=[],
        ),
        persuasion=Persuasion(
            chosen_plan="plan_delay_01",
            frame="cost",
            timing="at_plug_in",
            uplift_mean=0.34,
            uplift_p10=0.22,
            propensity=0.68,
            explored=False,
        ),
        allocation=Allocation(
            selected=True,
            shadow_price=12.5,
            slot="2026-10-10T22:30:00+05:30",
        ),
        language=Language(
            message="Charge at 10:30 PM tonight to save ₹51 and support grid stability during evening peak hours.",
            facts_used={"saving_inr": 51.3, "start_time": "22:30", "journey_conf": 0.94},
            verified=True,
            source="template",
        ),
        outcome=Outcome(
            adopted=True,
            kwh_shifted=18.4,
            opted_out=False,
            reward=28.6,
        ),
        fail_silent=False,
        error=None,
    )

    # 2. Safety Veto Case (Crucial Hackathon Moment #1)
    veto_record = DecisionRecord(
        decision_id="d_002_safety_veto",
        run_id="run_20261010_eval_01",
        sim_time="2026-10-10T19:15:00+05:30",
        user_id="user_delhi_1088",
        ev={
            "model": "MG ZS EV",
            "battery_kwh": 50.3,
            "current_soc": 0.18,
            "target_soc": 0.85,
            "max_ac_kw": 7.4,
            "plugged_in": True,
            "connector_type": "Type 2",
            "location": "home",
        },
        journey=Journey(
            p_arrive_above_reserve=0.82,
            arrival_soc_q10=0.06,
            arrival_soc_q50=0.15,
            arrival_soc_q90=0.24,
            reserve_soc=0.10,
        ),
        battery=BatteryView(
            stress_score=0.45,
            soh_delta_range_pct=(-0.010, 0.025),
        ),
        station=StationView(
            eta_wait_min_q50=0.0,
            eta_wait_min_q90=0.0,
            reliability=0.99,
        ),
        grid=GridView(
            stress_q50=0.92,
            stress_q90=0.98,
            green_window_start="2026-10-10T23:00:00+05:30",
            green_window_end="2026-10-11T05:30:00+05:30",
        ),
        plans=[
            Plan(
                plan_id="plan_default_02",
                type="default",
                start="2026-10-10T19:15:00+05:30",
                kw=7.4,
                where="home",
                outcomes={
                    "cost_inr": 232.0,
                    "journey_conf_lb": 0.95,
                    "grid_value": -0.90,
                    "battery_stress_delta": 0.15,
                    "wait_min": 0.0,
                },
            ),
            Plan(
                plan_id="plan_delay_risky",
                type="delay",
                start="2026-10-11T02:00:00+05:30",
                kw=7.4,
                where="home",
                outcomes={
                    "cost_inr": 154.0,
                    "journey_conf_lb": 0.82,  # BELOW 0.90 THRESHOLD!
                    "grid_value": 1.20,
                    "battery_stress_delta": -0.04,
                    "wait_min": 0.0,
                },
            ),
        ],
        safety=Safety(
            invariants_ok=False,
            cedar="DENY",
            vetoed=[
                "plan_delay_risky: journey_conf_lb 0.82 < threshold 0.90",
                "plan_delay_risky: arrival_soc_q10 0.06 < reserve 0.10",
            ],
        ),
        persuasion=Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=0.0,
            uplift_p10=0.0,
            propensity=1.0,
            explored=False,
        ),
        allocation=Allocation(
            selected=False,
            shadow_price=0.0,
            slot=None,
        ),
        language=Language(
            message=None,
            facts_used={},
            verified=True,
            source="none",
        ),
        outcome=Outcome(
            adopted=None,
            kwh_shifted=0.0,
            opted_out=False,
            reward=0.0,
        ),
        fail_silent=False,
        error=None,
    )

    # 3. Learned Silence / None Arm Case (Hackathon Moment #2)
    silence_record = DecisionRecord(
        decision_id="d_003_learned_silence",
        run_id="run_20261010_eval_01",
        sim_time="2026-10-10T19:30:00+05:30",
        user_id="user_delhi_0044",
        ev={
            "model": "Mahindra XUV400",
            "battery_kwh": 39.4,
            "current_soc": 0.65,
            "target_soc": 0.90,
            "max_ac_kw": 7.2,
            "plugged_in": True,
            "connector_type": "Type 2",
            "location": "home",
        },
        journey=Journey(
            p_arrive_above_reserve=0.98,
            arrival_soc_q10=0.42,
            arrival_soc_q50=0.55,
            arrival_soc_q90=0.68,
            reserve_soc=0.10,
        ),
        battery=BatteryView(
            stress_score=0.18,
            soh_delta_range_pct=(-0.005, 0.020),
        ),
        station=StationView(
            eta_wait_min_q50=0.0,
            eta_wait_min_q90=0.0,
            reliability=0.99,
        ),
        grid=GridView(
            stress_q50=0.91,
            stress_q90=0.97,
            green_window_start="2026-10-10T22:30:00+05:30",
            green_window_end="2026-10-11T05:30:00+05:30",
        ),
        plans=[
            Plan(
                plan_id="plan_default_03",
                type="default",
                start="2026-10-10T19:30:00+05:30",
                kw=7.2,
                where="home",
                outcomes={
                    "cost_inr": 110.0,
                    "journey_conf_lb": 0.99,
                    "grid_value": -0.75,
                    "battery_stress_delta": 0.08,
                    "wait_min": 0.0,
                },
            ),
            Plan(
                plan_id="plan_delay_03",
                type="delay",
                start="2026-10-10T23:00:00+05:30",
                kw=7.2,
                where="home",
                outcomes={
                    "cost_inr": 78.0,
                    "journey_conf_lb": 0.98,
                    "grid_value": 1.15,
                    "battery_stress_delta": -0.02,
                    "wait_min": 0.0,
                },
            ),
        ],
        safety=Safety(
            invariants_ok=True,
            cedar="ALLOW",
            vetoed=[],
        ),
        persuasion=Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=-0.03,  # User shifts spontaneously; nudge creates fatigue without added uplift
            uplift_p10=-0.08,
            propensity=0.92,
            explored=False,
        ),
        allocation=Allocation(
            selected=False,
            shadow_price=0.0,
            slot=None,
        ),
        language=Language(
            message=None,
            facts_used={},
            verified=True,
            source="none",
        ),
        outcome=Outcome(
            adopted=True,  # User spontaneously shifts anyway
            kwh_shifted=9.8,
            opted_out=False,
            reward=14.2,
        ),
        fail_silent=False,
        error=None,
    )

    return [
        nudge_record.model_dump(mode="json"),
        veto_record.model_dump(mode="json"),
        silence_record.model_dump(mode="json"),
    ]


def make_metrics_timeline() -> dict:
    """Generate 24-hour / 96-timestep timeline with evening heatwave event."""
    timesteps = []
    base_hours = 24
    feeder_cap = 12.0

    for step in range(base_hours * 4):
        hour = step / 4.0
        time_str = f"2026-10-10T{int(hour):02d}:{int((hour % 1) * 60):02d}:00+05:30"

        # Base non-EV demand (MW)
        if 0 <= hour < 6:
            base_load = 4.2 + 0.3 * (hour / 6)
            solar_gen = 0.0
        elif 6 <= hour < 10:
            base_load = 4.5 + 2.0 * ((hour - 6) / 4)
            solar_gen = 0.8 * ((hour - 6) / 4)
        elif 10 <= hour < 16:
            base_load = 6.5 + 0.8 * (1 - abs(hour - 13) / 3)
            solar_gen = 3.8 * (1 - ((hour - 13) / 3) ** 2)
        elif 16 <= hour < 22:
            base_load = 7.5 + 1.6 * (1 - abs(hour - 19.5) / 2.5)  # Evening non-EV peak
            solar_gen = max(0.0, 0.4 * (1 - (hour - 16) / 2))
        else:
            base_load = 6.2 - 1.8 * ((hour - 22) / 2)
            solar_gen = 0.0

        is_heatwave = 18.0 <= hour <= 21.75
        heatwave_extra = 1.4 if is_heatwave else 0.0

        # Baseline EV Load (uncontrolled + broadcast panic spikes)
        if 18.0 <= hour <= 22.0:
            baseline_ev = 3.6 + heatwave_extra + 0.4 * (1 - abs(hour - 20) / 2)
        elif 10.0 <= hour <= 16.0:
            baseline_ev = 0.6  # Under-utilized solar window
        else:
            baseline_ev = 1.2

        # GridNudge EV Load (staggered, anti-herding, shifted to solar & night)
        if 18.0 <= hour <= 22.0:
            gridnudge_ev = 1.2  # Curtailed peak without rebound!
        elif 11.0 <= hour <= 15.0:
            gridnudge_ev = 2.4  # Absorbs solar
        elif 22.5 <= hour or hour <= 4.0:
            gridnudge_ev = 2.6  # Smooth staggered off-peak night charging
        else:
            gridnudge_ev = 1.1

        baseline_total = base_load + heatwave_extra + baseline_ev
        gridnudge_total = base_load + heatwave_extra + gridnudge_ev

        timesteps.append(
            {
                "step": step,
                "sim_time": time_str,
                "hour": round(hour, 2),
                "is_peak_window": 17.0 <= hour <= 23.0,
                "is_heatwave": is_heatwave,
                "feeder_capacity_mw": feeder_cap,
                "base_load_mw": round(base_load + heatwave_extra, 2),
                "solar_gen_mw": round(max(0.0, solar_gen), 2),
                "baseline_ev_load_mw": round(baseline_ev, 2),
                "gridnudge_ev_load_mw": round(gridnudge_ev, 2),
                "baseline_total_load_mw": round(baseline_total, 2),
                "gridnudge_total_load_mw": round(gridnudge_total, 2),
                "baseline_stress": round(baseline_total / feeder_cap, 3),
                "gridnudge_stress": round(gridnudge_total / feeder_cap, 3),
                "nudges_delivered": 42 if 17.5 <= hour <= 19.5 else 0,
                "safety_vetoes": 6 if 17.5 <= hour <= 19.5 else 0,
                "learned_silence_count": 28 if 17.5 <= hour <= 19.5 else 0,
                "shadow_price_inr": 14.5 if 18.0 <= hour <= 21.0 else 0.0,
            }
        )

    return {
        "scenario": "heatwave_evening_stress",
        "provenance": "Simulation",
        "feeder_name": "Delhi_Substation_Feeder_F12",
        "timesteps": timesteps,
    }


def make_evaluation_summary() -> dict:
    """Generate benchmark comparison across B0 to B4 with confidence intervals."""
    return {
        "provenance": "Simulation",
        "n_seeds": 5,
        "n_users": 2000,
        "simulation_days": 7,
        "scenario": "heatwave",
        "policies": [
            {
                "id": "B0",
                "name": "Uncontrolled / Default",
                "description": "EVs charge at max power immediately upon plug-in",
                "peak_load_mw": {"mean": 13.42, "ci_low": 13.15, "ci_high": 13.68},
                "peak_reduction_pct": {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0},
                "kwh_shifted_daily": {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0},
                "nudges_per_user_day": {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0},
                "safety_violations": 0,
                "stranded_trips": 0,
                "mean_savings_inr_user_day": {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0},
                "opt_out_rate_pct": {"mean": 0.0, "ci_low": 0.0, "ci_high": 0.0},
            },
            {
                "id": "B1",
                "name": "Broadcast Peak Alert",
                "description": "Generic cost-saving notification broadcast to all plugged EVs at peak",
                "peak_load_mw": {"mean": 12.85, "ci_low": 12.58, "ci_high": 13.12},
                "peak_reduction_pct": {"mean": 4.25, "ci_low": 3.80, "ci_high": 4.70},
                "kwh_shifted_daily": {"mean": 1840.0, "ci_low": 1710.0, "ci_high": 1960.0},
                "nudges_per_user_day": {"mean": 2.85, "ci_low": 2.80, "ci_high": 2.90},
                "safety_violations": 14,  # Unsafe delay caused stranding
                "stranded_trips": 5,
                "mean_savings_inr_user_day": {"mean": 18.5, "ci_low": 16.2, "ci_high": 20.8},
                "opt_out_rate_pct": {"mean": 8.4, "ci_low": 7.6, "ci_high": 9.2},
            },
            {
                "id": "B2",
                "name": "Rule-Based Safe Planner",
                "description": "Safe plans only, but static rules with no uplift learning or budget",
                "peak_load_mw": {"mean": 12.18, "ci_low": 11.95, "ci_high": 12.40},
                "peak_reduction_pct": {"mean": 9.24, "ci_low": 8.60, "ci_high": 9.85},
                "kwh_shifted_daily": {"mean": 3210.0, "ci_low": 3040.0, "ci_high": 3380.0},
                "nudges_per_user_day": {"mean": 1.95, "ci_low": 1.90, "ci_high": 2.00},
                "safety_violations": 0,
                "stranded_trips": 0,
                "mean_savings_inr_user_day": {"mean": 29.4, "ci_low": 27.1, "ci_high": 31.7},
                "opt_out_rate_pct": {"mean": 4.8, "ci_low": 4.2, "ci_high": 5.4},
            },
            {
                "id": "B3",
                "name": "Bandit Without Allocator",
                "description": "Contextual bandit learns personalization, but uncoordinated timing creates rebound",
                "peak_load_mw": {"mean": 11.92, "ci_low": 11.70, "ci_high": 12.15},
                "peak_reduction_pct": {"mean": 11.18, "ci_low": 10.45, "ci_high": 11.90},
                "kwh_shifted_daily": {"mean": 4120.0, "ci_low": 3950.0, "ci_high": 4290.0},
                "nudges_per_user_day": {"mean": 1.45, "ci_low": 1.38, "ci_high": 1.52},
                "safety_violations": 0,
                "stranded_trips": 0,
                "mean_savings_inr_user_day": {"mean": 36.8, "ci_low": 34.2, "ci_high": 39.4},
                "opt_out_rate_pct": {"mean": 2.6, "ci_low": 2.1, "ci_high": 3.1},
            },
            {
                "id": "B4",
                "name": "GridNudge (Full System)",
                "description": "Safety gate + uplift bandit with none arm + fleet budget allocator & staggering",
                "peak_load_mw": {"mean": 10.74, "ci_low": 10.55, "ci_high": 10.92},
                "peak_reduction_pct": {"mean": 19.97, "ci_low": 18.85, "ci_high": 21.10},
                "kwh_shifted_daily": {"mean": 5480.0, "ci_low": 5290.0, "ci_high": 5670.0},
                "nudges_per_user_day": {"mean": 0.72, "ci_low": 0.68, "ci_high": 0.76},
                "safety_violations": 0,
                "stranded_trips": 0,
                "mean_savings_inr_user_day": {"mean": 48.2, "ci_low": 45.6, "ci_high": 50.8},
                "opt_out_rate_pct": {"mean": 0.8, "ci_low": 0.5, "ci_high": 1.1},
            },
        ],
    }


def make_calibration() -> dict:
    """Generate reliability diagram calibration data for Journey Confidence."""
    return {
        "metric": "Journey Confidence P(arrival SOC >= reserve)",
        "provenance": "Simulation",
        "held_out_trips_count": 5000,
        "expected_calibration_error": 0.021,
        "max_calibration_error": 0.038,
        "bins": [
            {"bin_start": 0.0, "bin_end": 0.1, "mean_predicted": 0.06, "observed_freq": 0.05, "count": 120},
            {"bin_start": 0.1, "bin_end": 0.2, "mean_predicted": 0.16, "observed_freq": 0.17, "count": 180},
            {"bin_start": 0.2, "bin_end": 0.3, "mean_predicted": 0.25, "observed_freq": 0.24, "count": 210},
            {"bin_start": 0.3, "bin_end": 0.4, "mean_predicted": 0.36, "observed_freq": 0.35, "count": 290},
            {"bin_start": 0.4, "bin_end": 0.5, "mean_predicted": 0.45, "observed_freq": 0.47, "count": 350},
            {"bin_start": 0.5, "bin_end": 0.6, "mean_predicted": 0.55, "observed_freq": 0.54, "count": 420},
            {"bin_start": 0.6, "bin_end": 0.7, "mean_predicted": 0.65, "observed_freq": 0.64, "count": 560},
            {"bin_start": 0.7, "bin_end": 0.8, "mean_predicted": 0.75, "observed_freq": 0.76, "count": 780},
            {"bin_start": 0.8, "bin_end": 0.9, "mean_predicted": 0.85, "observed_freq": 0.84, "count": 1050},
            {"bin_start": 0.9, "bin_end": 1.0, "mean_predicted": 0.95, "observed_freq": 0.94, "count": 1040},
        ],
    }


def make_flexibility() -> dict:
    """Generate 24h flexibility forecast envelope vs adoption-weighted forecast."""
    timesteps = []
    for h in range(24):
        # Physical available flexibility vs learned adoption-weighted response
        if 17 <= h <= 23:
            phys_p50 = 3200.0 + 800.0 * (1 - abs(h - 20) / 3)
            adopt_p50 = phys_p50 * 0.68
        elif 10 <= h <= 16:
            phys_p50 = 1800.0
            adopt_p50 = phys_p50 * 0.45
        else:
            phys_p50 = 1200.0
            adopt_p50 = phys_p50 * 0.55

        timesteps.append(
            {
                "hour": h,
                "label": f"{h:02d}:00",
                "physical_envelope_kw": {
                    "p10": round(phys_p50 * 0.85, 1),
                    "p50": round(phys_p50, 1),
                    "p90": round(phys_p50 * 1.15, 1),
                },
                "adoption_weighted_kw": {
                    "p10": round(adopt_p50 * 0.78, 1),
                    "p50": round(adopt_p50, 1),
                    "p90": round(adopt_p50 * 1.12, 1),
                },
            }
        )

    return {
        "provenance": "Simulation",
        "horizon_hours": 24,
        "peak_window_hours": "17:00-23:00",
        "timesteps": timesteps,
    }


def main():
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    files = {
        "decisions.sample.json": make_decisions_sample(),
        "metrics.timeline.json": make_metrics_timeline(),
        "evaluation.summary.json": make_evaluation_summary(),
        "calibration.json": make_calibration(),
        "flexibility.json": make_flexibility(),
    }

    for name, content in files.items():
        path = FIXTURES_DIR / name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)
        print(f"Generated fixture: {path}")


if __name__ == "__main__":
    main()
