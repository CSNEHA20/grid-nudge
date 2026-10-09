"""Planner module for GridNudge.

Generates candidate charging plans for eligible electric vehicles and deterministically
predicts their outcomes (cost, journey confidence lower bound, grid value, battery stress delta,
queue wait, and new peak creation) given perception outputs and physical constraints.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

from gridnudge.contracts import Plan
from gridnudge.perception.battery import compute_battery_stress_score
from gridnudge.perception.journey import estimate_journey_confidence


def get_tariff_rate_inr(hour_of_day: float) -> float:
    """Return ToU electricity tariff in INR/kWh for Delhi based on DERC order.

    Solar hours (10:00 - 16:00): 4.50 INR/kWh
    Evening peak (17:00 - 23:00): 8.50 INR/kWh
    Night / Standard (23:00 - 10:00, 16:00 - 17:00): 6.00 INR/kWh
    """
    h = float(hour_of_day) % 24.0
    if 10.0 <= h < 16.0:
        return 4.50
    elif 17.0 <= h < 23.0:
        return 8.50
    else:
        return 6.00


def calculate_charging_cost_inr(
    start_hour: float,
    duration_hours: float,
    power_kw: float,
    efficiency: float = 0.92,
) -> float:
    """Calculate total energy cost in INR across time-of-use tariff intervals."""
    if duration_hours <= 0.0 or power_kw <= 0.0:
        return 0.0

    # Integrate across 15-minute segments
    n_segments = max(1, int(np.ceil(duration_hours * 4.0)))
    segment_duration = duration_hours / n_segments
    total_cost = 0.0

    for i in range(n_segments):
        hour = (start_hour + i * segment_duration) % 24.0
        rate = get_tariff_rate_inr(hour)
        grid_kwh = (power_kw * segment_duration) / efficiency
        total_cost += grid_kwh * rate

    return round(float(total_cost), 2)


def generate_candidate_plans(
    ev_context: Dict[str, Any],
    sim_time_iso: str,
    hour_of_day: float = 18.0,
    grid_stress: float = 0.85,
    solar_share: float = 0.20,
    ambient_temp_c: float = 30.0,
    green_window_start: Optional[str] = None,
    station_views: Optional[Dict[int, Any]] = None,
    feeder_capacity_mw: float = 12.0,
    current_feeder_load_mw: float = 9.5,
    user_id: Optional[str] = None,
    commute_distance_km: Optional[float] = None,
    **kwargs: Any,
) -> List[Plan]:
    """Enumerate candidate charging plans and compute predicted outcomes for an EV.

    Candidate Plan Types:
    - default: Uncontrolled charging starting immediately at full power until target SOC.
    - delay: Postpone charging start to green or off-peak night window before departure deadline.
    - slow_charge: Reduced power charging spread across the available window (battery and grid friendly).
    - top_up_now: Protective immediate burst charging when journey confidence or battery is at risk.
    - relocate: Alternate public charging station with lower predicted queue wait (if mobile).

    Args:
        ev_context: Vehicle state dictionary (battery_kwh, current_soc, target_soc, charger_kw,
            commute_km, hours_until_departure, has_home_charging, location, etc.).
        sim_time_iso: Current simulation ISO 8601 timestamp.
        hour_of_day: Current decimal hour of day (0.0 to 23.99).
        grid_stress: Current or forecast grid feeder stress ratio.
        solar_share: Current or forecast renewable generation share.
        ambient_temp_c: Ambient temperature in degrees Celsius.
        green_window_start: Optional ISO timestamp or time string for green charging window.
        station_views: Optional dictionary mapping station_id to StationView perception objects.
        feeder_capacity_mw: Total feeder transformer capacity in MW.
        current_feeder_load_mw: Current total feeder load in MW.
        user_id: Optional user identifier.
        commute_distance_km: Optional commute distance override in km.

    Returns:
        List of typed Plan objects.
    """
    battery_kwh = float(ev_context.get("battery_kwh", 40.0))
    current_soc = float(ev_context.get("current_soc", 0.30))
    target_soc = float(ev_context.get("target_soc", 0.90))
    charger_kw = float(ev_context.get("charger_kw", 7.4))
    default_commute = commute_distance_km if commute_distance_km is not None else 45.0
    commute_km = float(ev_context.get("commute_km", default_commute))
    base_wh_km = float(ev_context.get("base_wh_km", 160.0))
    hours_until_departure = float(ev_context.get("hours_until_departure", 8.0))
    has_home_charging = bool(ev_context.get("has_home_charging", True))
    location = str(ev_context.get("location", "home" if has_home_charging else "station_1"))

    # Parse sim_time
    try:
        base_time = datetime.fromisoformat(sim_time_iso.replace("Z", "+00:00"))
    except Exception:
        base_time = datetime(2026, 10, 10, int(hour_of_day), int((hour_of_day % 1) * 60))

    energy_needed_kwh = max(0.0, (target_soc - current_soc) * battery_kwh)
    charging_efficiency = 0.92

    plans: List[Plan] = []

    # -------------------------------------------------------------
    # 1. DEFAULT PLAN: Immediate charging at max power
    # -------------------------------------------------------------
    full_charge_hours = (energy_needed_kwh / (charger_kw * charging_efficiency)) if charger_kw > 0 else 0.0
    effective_charge_hours = min(hours_until_departure, full_charge_hours)

    delivered_kwh_default = effective_charge_hours * charger_kw * charging_efficiency
    resulting_soc_default = min(1.0, current_soc + (delivered_kwh_default / battery_kwh))

    journey_default = estimate_journey_confidence(
        departure_soc=resulting_soc_default,
        battery_kwh=battery_kwh,
        distance_km=commute_km,
        base_wh_km=base_wh_km,
        ambient_temp_c=ambient_temp_c,
    )

    cost_default = calculate_charging_cost_inr(
        start_hour=hour_of_day,
        duration_hours=effective_charge_hours,
        power_kw=charger_kw,
    )

    stress_default = compute_battery_stress_score(
        soc=resulting_soc_default,
        charging_kw=charger_kw,
        battery_kwh=battery_kwh,
        ambient_temp_c=ambient_temp_c,
        hours_at_high_soc=max(0.0, hours_until_departure - full_charge_hours),
    )

    # Grid value is negative if charging during high-stress peak hours
    is_in_peak = 17.0 <= (hour_of_day % 24.0) < 23.0
    if is_in_peak:
        grid_val_default = round(-1.0 * grid_stress * (delivered_kwh_default / 10.0), 2)
    else:
        grid_val_default = 0.0

    wait_min_default = 0.0
    if not has_home_charging and station_views and location.startswith("station_"):
        try:
            st_id = int(location.split("_")[1])
            if st_id in station_views:
                wait_min_default = float(station_views[st_id].eta_wait_min_q50)
        except Exception:
            wait_min_default = 5.0

    creates_peak_default = (current_feeder_load_mw + (charger_kw / 1000.0)) > feeder_capacity_mw

    plan_default = Plan(
        plan_id=f"plan_default_{ev_context.get('user_id', 0)}",
        type="default",
        start=base_time.isoformat(),
        kw=charger_kw,
        where=location,
        outcomes={
            "cost_inr": cost_default,
            "journey_conf_lb": journey_default.p_arrive_above_reserve,
            "grid_value": grid_val_default,
            "battery_stress_delta": 0.0,
            "wait_min": wait_min_default,
            "creates_new_peak": creates_peak_default,
        },
    )
    plans.append(plan_default)

    # -------------------------------------------------------------
    # 2. DELAY PLAN: Postpone charging start to off-peak night
    # -------------------------------------------------------------
    # Target delay to off-peak start (23:00) or night window
    hours_to_offpeak = (23.0 - (hour_of_day % 24.0)) % 24.0
    if hours_to_offpeak == 0.0 and is_in_peak:
        hours_to_offpeak = 0.5

    # Safe delay should fit charging before departure
    # Try a delay of hours_to_offpeak, or a standard 3.5h delay
    delay_hours = hours_to_offpeak if hours_to_offpeak > 0 else 3.5

    time_available_after_delay = max(0.0, hours_until_departure - delay_hours)
    delay_charge_hours = min(time_available_after_delay, full_charge_hours)
    delivered_kwh_delay = delay_charge_hours * charger_kw * charging_efficiency
    resulting_soc_delay = min(1.0, current_soc + (delivered_kwh_delay / battery_kwh))

    journey_delay = estimate_journey_confidence(
        departure_soc=resulting_soc_delay,
        battery_kwh=battery_kwh,
        distance_km=commute_km,
        base_wh_km=base_wh_km,
        ambient_temp_c=max(20.0, ambient_temp_c - 5.0),  # Cooler night temp
    )

    delay_start_hour = (hour_of_day + delay_hours) % 24.0
    cost_delay = calculate_charging_cost_inr(
        start_hour=delay_start_hour,
        duration_hours=delay_charge_hours,
        power_kw=charger_kw,
    )

    stress_delay = compute_battery_stress_score(
        soc=resulting_soc_delay,
        charging_kw=charger_kw,
        battery_kwh=battery_kwh,
        ambient_temp_c=max(20.0, ambient_temp_c - 5.0),
        hours_at_high_soc=max(0.0, time_available_after_delay - full_charge_hours),
    )
    stress_delta_delay = round(stress_delay - stress_default, 4)

    # Positive grid value: energy shifted out of peak into off-peak
    shifted_kwh = delivered_kwh_delay if is_in_peak else (delivered_kwh_default * 0.5)
    grid_val_delay = round(grid_stress * (shifted_kwh / 10.0) * 1.5, 2)

    delay_start_time = base_time + timedelta(hours=delay_hours)
    plan_delay = Plan(
        plan_id=f"plan_delay_{ev_context.get('user_id', 0)}",
        type="delay",
        start=delay_start_time.isoformat(),
        kw=charger_kw,
        where=location,
        outcomes={
            "cost_inr": cost_delay,
            "journey_conf_lb": journey_delay.p_arrive_above_reserve,
            "grid_value": grid_val_delay,
            "battery_stress_delta": stress_delta_delay,
            "wait_min": wait_min_default,
            "creates_new_peak": False,
        },
    )
    plans.append(plan_delay)

    # -------------------------------------------------------------
    # 3. SLOW CHARGE PLAN: Low power charging spread over window
    # -------------------------------------------------------------
    slow_kw = max(2.5, min(charger_kw * 0.5, 3.3))
    slow_charge_hours = (energy_needed_kwh / (slow_kw * charging_efficiency)) if slow_kw > 0 else 0.0

    if slow_charge_hours <= hours_until_departure * 1.05 and charger_kw > slow_kw:
        effective_slow_hours = min(hours_until_departure, slow_charge_hours)
        delivered_slow = effective_slow_hours * slow_kw * charging_efficiency
        resulting_soc_slow = min(1.0, current_soc + (delivered_slow / battery_kwh))

        journey_slow = estimate_journey_confidence(
            departure_soc=resulting_soc_slow,
            battery_kwh=battery_kwh,
            distance_km=commute_km,
            base_wh_km=base_wh_km,
            ambient_temp_c=ambient_temp_c,
        )

        cost_slow = calculate_charging_cost_inr(
            start_hour=hour_of_day,
            duration_hours=effective_slow_hours,
            power_kw=slow_kw,
        )

        stress_slow = compute_battery_stress_score(
            soc=resulting_soc_slow,
            charging_kw=slow_kw,
            battery_kwh=battery_kwh,
            ambient_temp_c=ambient_temp_c,
            hours_at_high_soc=0.5,
        )
        stress_delta_slow = round(stress_slow - stress_default, 4)

        # Reduced peak demand yields positive grid value
        peak_reduction_kw = (charger_kw - slow_kw)
        grid_val_slow = round((peak_reduction_kw * grid_stress) / 5.0, 2)

        plan_slow = Plan(
            plan_id=f"plan_slow_{ev_context.get('user_id', 0)}",
            type="slow_charge",
            start=base_time.isoformat(),
            kw=slow_kw,
            where=location,
            outcomes={
                "cost_inr": cost_slow,
                "journey_conf_lb": journey_slow.p_arrive_above_reserve,
                "grid_value": grid_val_slow,
                "battery_stress_delta": stress_delta_slow,
                "wait_min": wait_min_default,
                "creates_new_peak": False,
            },
        )
        plans.append(plan_slow)

    # -------------------------------------------------------------
    # 4. TOP-UP NOW PLAN: Protective charging when SOC/confidence is at risk
    # -------------------------------------------------------------
    # E.g. If current SOC is low or journey confidence under default is vulnerable (< 0.92)
    # or user has tight departure deadline (< 3 hours)
    if current_soc < 0.40 or journey_default.p_arrive_above_reserve < 0.92 or hours_until_departure < 4.0:
        boost_kw = min(charger_kw * 1.5, 22.0) if charger_kw > 7.4 else charger_kw
        top_up_hours = min(hours_until_departure, (energy_needed_kwh / (boost_kw * charging_efficiency)))
        delivered_top = top_up_hours * boost_kw * charging_efficiency
        resulting_soc_top = min(1.0, current_soc + (delivered_top / battery_kwh))

        journey_top = estimate_journey_confidence(
            departure_soc=resulting_soc_top,
            battery_kwh=battery_kwh,
            distance_km=commute_km,
            base_wh_km=base_wh_km,
            ambient_temp_c=ambient_temp_c,
        )

        cost_top = calculate_charging_cost_inr(
            start_hour=hour_of_day,
            duration_hours=top_up_hours,
            power_kw=boost_kw,
        )

        plan_top = Plan(
            plan_id=f"plan_top_up_{ev_context.get('user_id', 0)}",
            type="top_up_now",
            start=base_time.isoformat(),
            kw=boost_kw,
            where=location,
            outcomes={
                "cost_inr": cost_top,
                "journey_conf_lb": journey_top.p_arrive_above_reserve,
                "grid_value": -0.5,  # Protective prioritization over grid
                "battery_stress_delta": 0.05,
                "wait_min": wait_min_default,
                "creates_new_peak": False,
            },
        )
        plans.append(plan_top)

    # -------------------------------------------------------------
    # 5. RELOCATE PLAN: Alternative public station if queue is long
    # -------------------------------------------------------------
    if not has_home_charging and station_views and wait_min_default > 15.0:
        # Find station with lowest wait
        best_station_id = None
        lowest_wait = wait_min_default

        for st_id, s_view in station_views.items():
            if s_view.reliability > 0.5 and s_view.eta_wait_min_q50 < lowest_wait:
                lowest_wait = s_view.eta_wait_min_q50
                best_station_id = st_id

        if best_station_id is not None:
            plan_relocate = Plan(
                plan_id=f"plan_relocate_{ev_context.get('user_id', 0)}",
                type="relocate",
                start=(base_time + timedelta(minutes=15)).isoformat(),  # 15m transit
                kw=50.0,
                where=f"station_{best_station_id}",
                outcomes={
                    "cost_inr": cost_default,
                    "journey_conf_lb": journey_default.p_arrive_above_reserve,
                    "grid_value": 0.8,
                    "battery_stress_delta": -0.01,
                    "wait_min": lowest_wait,
                    "creates_new_peak": False,
                },
            )
            plans.append(plan_relocate)

    return plans
