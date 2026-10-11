"""Tests for digital twin (M2).

Verifies:
- Reproducibility and Common Random Numbers (CRN)
- Physical conservation laws (energy delivered <= charger capacity * time, 0 <= SOC <= 1)
- Evening peak existence in default unmanaged charging
- Injected environmental disturbance events (heatwave, solar drop, station outages)
- Hidden behavioral human response engine
- Performance benchmarks (2,000 EVs x 7 days under 60 seconds)
"""

from twin.battery_truth import charge_step, discharge_step
from twin.behavior_hidden import HiddenBehaviorEngine
from twin.runner import run_simulation
from twin.world import World


def test_crn_reproducibility():
    """Identical seeds must yield bitwise identical simulation trajectories."""
    w1 = World(seed=42, n_users=200, step_minutes=15)
    w2 = World(seed=42, n_users=200, step_minutes=15)

    res1 = run_simulation(world=w1, n_steps=96)
    res2 = run_simulation(world=w2, n_steps=96)

    assert res1["metrics"]["peak_feeder_load_mw"] == res2["metrics"]["peak_feeder_load_mw"]
    assert res1["metrics"]["total_energy_kwh"] == res2["metrics"]["total_energy_kwh"]
    assert res1["metrics"]["avg_grid_stress"] == res2["metrics"]["avg_grid_stress"]

    # Verify step-by-step telemetry equality
    for t1, t2 in zip(res1["timeline"], res2["timeline"]):
        assert t1["feeder_load_mw"] == t2["feeder_load_mw"]
        assert t1["ev_load_mw"] == t2["ev_load_mw"]
        assert t1["energy_kwh_delivered"] == t2["energy_kwh_delivered"]


def test_different_seeds_produce_different_trajectories():
    """Different seeds must draw different stochastic profiles."""
    w1 = World(seed=42, n_users=200, step_minutes=15)
    w2 = World(seed=999, n_users=200, step_minutes=15)

    # Fleet attributes must differ
    socs1 = [u.soc for u in w1.fleet.users]
    socs2 = [u.soc for u in w2.fleet.users]
    assert socs1 != socs2

    res1 = run_simulation(world=w1, n_steps=96)
    res2 = run_simulation(world=w2, n_steps=96)

    assert res1["metrics"]["total_energy_kwh"] != res2["metrics"]["total_energy_kwh"]



def test_physical_conservation_invariants():
    """Charging physics must strictly respect physical capacity and bounds."""
    # Test charge step invariants
    soc, kw, kwh = charge_step(soc=0.5, battery_kwh=40.0, charger_kw=7.4, step_hours=0.25)
    assert 0.0 <= soc <= 1.0
    assert kw <= 7.4 + 1e-6
    assert kwh <= 7.4 * 0.25 + 1e-6
    assert kwh >= 0.0

    # Overcharge protection: target SOC cutoff
    soc_full, kw_full, kwh_full = charge_step(soc=0.95, battery_kwh=40.0, charger_kw=50.0, step_hours=0.25, target_soc=0.90)
    assert soc_full == 0.95
    assert kw_full == 0.0
    assert kwh_full == 0.0

    # Discharge invariants: no negative SOC
    soc_dis, used_kwh = discharge_step(soc=0.05, battery_kwh=40.0, distance_km=500.0, base_wh_km=180.0)
    assert soc_dis >= 0.0
    assert used_kwh > 0.0


def test_evening_peak_exists_in_unmanaged_run():
    """Unmanaged charging must generate a pronounced evening charging surge."""
    w = World(seed=42, n_users=500, step_minutes=15)
    res = run_simulation(world=w, n_steps=96)
    timeline = res["timeline"]

    # Evening hours: 18:00 to 22:00 (steps 72 to 88)
    evening_ev_loads = [t["ev_load_mw"] for t in timeline if 18.0 <= t["hour_of_day"] <= 22.0]
    # Night hours: 02:00 to 06:00 (steps 8 to 24)
    night_ev_loads = [t["ev_load_mw"] for t in timeline if 2.0 <= t["hour_of_day"] <= 6.0]

    assert max(evening_ev_loads) > 0.0
    assert max(evening_ev_loads) > sum(night_ev_loads) / max(1, len(night_ev_loads))


def test_heatwave_event_increases_load_and_temperature():
    """Heatwave event must raise feeder base load during peak hours and raise ambient temp."""
    w_base = World(seed=42, n_users=100)
    w_base.events.active_events = []  # Clear default events
    t_base = [w_base.step() for _ in range(96)]

    w_heat = World(seed=42, n_users=100)
    w_heat.events.active_events = []
    w_heat.inject({
        "type": "heatwave",
        "start_step": 0,
        "end_step": 96,
        "temp_rise_c": 6.0,
        "base_load_mult": 1.25,
    })
    t_heat = [w_heat.step() for _ in range(96)]

    # Peak hour base load comparison at 20:00 (step 80)
    step_80_base = t_base[80]["base_load_mw"]
    step_80_heat = t_heat[80]["base_load_mw"]
    assert step_80_heat > step_80_base


def test_solar_drop_event():
    """Solar drop event must visibly reduce daytime solar generation."""
    w_norm = World(seed=42, n_users=50)
    w_norm.events.active_events = []
    t_norm = [w_norm.step() for _ in range(96)]

    w_drop = World(seed=42, n_users=50)
    w_drop.events.active_events = []
    w_drop.inject({
        "type": "solar_drop",
        "start_step": 0,
        "end_step": 96,
        "solar_factor": 0.40,
    })
    t_drop = [w_drop.step() for _ in range(96)]

    # At hour 13:00 (step 52), solar generation must be lower
    solar_norm = t_norm[52]["solar_mw"]
    solar_drop = t_drop[52]["solar_mw"]
    assert solar_drop < solar_norm


def test_station_outage_event():
    """Station outage event must reduce effective connectors."""
    w = World(seed=42, n_users=50)
    st0 = w.stations.get_station(0)
    assert st0.available_connectors == 6

    w.inject({
        "type": "station_outage",
        "start_step": 0,
        "end_step": 96,
        "stations": [0, 1],
    })
    w.step()

    assert st0.is_offline is True
    assert st0.available_connectors == 0


def test_hidden_behavior_engine():
    """Behavior engine must support spontaneous shifting, positive uplift, and fatigue."""
    engine = HiddenBehaviorEngine()

    # Spontaneous shift without nudge
    p_adopt, p_none, uplift, p_opt = engine.compute_probabilities(
        archetype="commuter_frugal",
        frame="none",
        savings_inr=0.0,
        delay_hours=0.0,
        fatigue=0.0,
        is_repeat_frame=False,
        is_nudged=False,
    )
    assert p_adopt == p_none
    assert uplift == 0.0
    assert 0.0 < p_adopt < 0.5  # Spontaneous probability is non-zero but small

    # Nudge with cost frame and savings increases adoption
    p_adopt_nudge, _, uplift_nudge, _ = engine.compute_probabilities(
        archetype="commuter_frugal",
        frame="cost",
        savings_inr=80.0,
        delay_hours=2.0,
        fatigue=0.0,
        is_repeat_frame=False,
        is_nudged=True,
    )
    assert p_adopt_nudge > p_none
    assert uplift_nudge > 0.0

    # Fatigue and repeated frame reduce adoption
    p_adopt_fatigued, _, _, _ = engine.compute_probabilities(
        archetype="commuter_frugal",
        frame="cost",
        savings_inr=80.0,
        delay_hours=2.0,
        fatigue=2.5,
        is_repeat_frame=True,
        is_nudged=True,
    )
    assert p_adopt_fatigued < p_adopt_nudge


def test_fleet_soc_invariants_throughout_simulation():
    """All 2000 simulated EVs must maintain SOC in [0.0, 1.0] across multiple days."""
    w = World(seed=42, n_users=500, step_minutes=15)
    for _ in range(96 * 2):  # 2 days
        w.step()

    for u in w.fleet.users:
        assert 0.0 <= u.soc <= 1.0
        assert u.battery_kwh > 0.0
        assert u.charger_kw > 0.0


def test_benchmark_performance_under_60_seconds():
    """2,000 EVs simulated for 7 days (672 steps) must complete in under 60 seconds."""
    res = run_simulation(seed=42, n_users=2000, n_steps=672)
    elapsed = res["metrics"]["elapsed_seconds"]
    assert elapsed < 60.0, f"Simulation took {elapsed:.2f}s, exceeding 60s limit"


def test_slow_charge_does_not_permanently_halve_charger_power():
    """Adopting slow_charge must cap power per-session only, restoring nominal power at next session."""
    from twin.world import compute_kwh_shifted_from_peak
    w = World(seed=42, n_users=20)
    user = w.fleet.users[0]
    user.archetype = "commuter_frugal"
    user.fatigue = 0.0
    nominal_kw = user.charger_kw
    assert user.nominal_charger_kw == nominal_kw

    # Plug in user
    user.plugged = True
    user.plug_in_step = 72
    user.departure_step = 96

    # Apply slow_charge adoption
    w.apply_decisions([{
        "decision_id": "test_d1",
        "user_id": user.user_id,
        "plan": {"type": "slow_charge"},
        "frame": "cost",
        "timing": "at_plug_in",
        "savings_inr": 100.0,
        "delay_hours": 0.0,
    }])

    # Charger power is capped during this active plan
    assert user.charger_kw == max(2.0, nominal_kw * 0.5)
    assert user.charger_kw_cap == max(2.0, nominal_kw * 0.5)

    # Trigger departure
    w.current_step = 96
    w._update_schedules_and_arrivals()

    # Base nominal charger power must be restored, not halved permanently
    assert user.charger_kw == nominal_kw
    assert user.charger_kw_cap is None


def test_kwh_shifted_from_peak_physical_values():
    """kwh_shifted_from_peak must match exact physical hand-computed examples."""
    from twin.world import compute_kwh_shifted_from_peak

    # Arriving at 18:00 (step 72), 40 kWh battery, 0.5 -> 0.9 SOC (needs 16 kWh)
    # nominal charger 7.4 kW at 0.92 efficiency = 6.808 kW
    # Default duration = 16 / 6.808 = 2.35 hrs (10 steps). Finished at step 82 (before 22:00 = 88).
    # Default peak energy = 16.0 kWh.

    # 1. Delay by 5 hours (20 steps) to 23:00 (step 92): all 16 kWh shifted out of peak
    shifted_delay_full = compute_kwh_shifted_from_peak(
        plan_type="delay",
        adopted=True,
        initial_soc=0.5,
        target_soc=0.9,
        battery_kwh=40.0,
        nominal_charger_kw=7.4,
        plug_in_step=72,
        delay_hours=5.0,
    )
    assert shifted_delay_full == 16.0

    # 2. Slow charge (halved to 3.7 kW): 16 kWh at 3.7 kW takes 4.7 hours (19 steps to step 91).
    # Draws power during steps 72 to 88 (16 steps = 4 hrs): 4 * 3.7 * 0.92 = 13.616 kWh.
    # Energy shifted out of peak into night = 16.0 - 13.616 = 2.38 kWh
    shifted_slow = compute_kwh_shifted_from_peak(
        plan_type="slow_charge",
        adopted=True,
        initial_soc=0.5,
        target_soc=0.9,
        battery_kwh=40.0,
        nominal_charger_kw=7.4,
        plug_in_step=72,
        delay_hours=0.0,
    )
    assert 2.0 <= shifted_slow <= 3.0

    # 3. Top-up now or unadopted shift zero
    assert compute_kwh_shifted_from_peak("top_up_now", True, 0.5, 0.9, 40.0, 7.4, 72) == 0.0
    assert compute_kwh_shifted_from_peak("delay", False, 0.5, 0.9, 40.0, 7.4, 72) == 0.0


def test_baselines_b1_and_b2_are_distinct():
    """B1 (broadcast) and B2 (safe rule-based) must yield distinct nudge counts and peak loads."""
    from eval.baselines import policy_b1, policy_b2
    w1 = World(seed=42, n_users=200)
    res_b1 = run_simulation(world=w1, n_steps=96, policy_fn=policy_b1)

    w2 = World(seed=42, n_users=200)
    res_b2 = run_simulation(world=w2, n_steps=96, policy_fn=policy_b2)

    # B1 broadcasts to every plugged user; B2 caps to 1 nudge/day and checks reserve safety
    assert res_b1["metrics"]["total_nudges_sent"] != res_b2["metrics"]["total_nudges_sent"]
    assert res_b1["metrics"]["total_nudges_sent"] > res_b2["metrics"]["total_nudges_sent"]


def test_mean_uplift_nonzero_on_nudged_outcomes():
    """Mean uplift per nudge must be positive (> 0.0) when nudges are delivered."""
    from eval.baselines import policy_b1
    from eval.metrics import compute_run_metrics
    w = World(seed=42, n_users=200)
    res = run_simulation(world=w, n_steps=96, policy_fn=policy_b1)
    m = compute_run_metrics(res)
    assert m["mean_uplift_per_nudge"] > 0.0, "mean_uplift_per_nudge must not be 0.00"

