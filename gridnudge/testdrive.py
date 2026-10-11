"""Digital Test Drive engine (M14).

Simulates a complete 52-week annual EV ownership experience for prospective buyers,
evaluating commuting distance, weekend road trips, home charging availability,
climate zone extremes, queue exposure, battery stress, and financial payback.
"""

from typing import Any, Dict, List
import numpy as np


def run_digital_test_drive(
    daily_commute_km: float = 35.0,
    weekend_trip_km: float = 120.0,
    home_charging_access: bool = True,
    climate_zone: str = "composite_delhi",
    current_monthly_fuel_inr: float = 8500.0,
    offpeak_tariff_inr: float = 4.5,
    battery_kwh: float = 40.5,
    seed: int = 42,
) -> Dict[str, Any]:
    """Run simulated 52-week EV ownership lifecycle.

    Returns:
        Structured test drive evaluation matching the dashboard schema.
    """
    rng = np.random.default_rng(seed)
    weeks = 52
    weekly_risk_timeline: List[str] = []
    weeks_at_risk = 0
    total_annual_kwh = 0.0

    # Weekly simulation
    for week in range(weeks):
        # Seasonality: weeks 18-24 are peak summer (heatwave 40-45C), weeks 48-4 are winter (10-15C)
        is_heatwave = 18 <= week <= 24
        is_winter = week >= 48 or week <= 3

        # Distance: 5 days commute + weekend trip probability (0.35)
        has_weekend_trip = rng.random() < 0.35
        wk_dist = (daily_commute_km * 5.0) + (weekend_trip_km if has_weekend_trip else 20.0)

        # Efficiency with temperature impact
        hvac_penalty = 1.25 if is_heatwave else (1.10 if is_winter else 1.0)
        wh_km = 145.0 * hvac_penalty
        wk_kwh = (wk_dist * wh_km) / 1000.0
        total_annual_kwh += wk_kwh

        # Risk assessment:
        risk_status = "SAFE"
        # 1. High single-day range risk vs battery size
        daily_max_kwh = (daily_commute_km * wh_km) / 1000.0
        if daily_max_kwh > (battery_kwh * 0.75):
            risk_status = "RANGE_STRESS"
            weeks_at_risk += 1
        elif not home_charging_access:
            # Public dependency: risk of queue delay or heatwave station outages
            if is_heatwave or (has_weekend_trip and wk_dist > 250.0):
                risk_status = "PUBLIC_QUEUE_RISK"
                weeks_at_risk += 1
        elif is_heatwave and has_weekend_trip:
            risk_status = "HEATWAVE_HVAC_RISK"
            weeks_at_risk += 1

        weekly_risk_timeline.append(risk_status)

    safe_weeks = weeks - weeks_at_risk
    confidence_pct = round(float((safe_weeks / weeks) * 100.0), 1)

    # Financial analysis
    monthly_kwh = total_annual_kwh / 12.0
    effective_rate = offpeak_tariff_inr if home_charging_access else (offpeak_tariff_inr * 1.8)
    monthly_ev_cost_inr = round(float(monthly_kwh * effective_rate), 0)
    monthly_savings_inr = round(float(max(0.0, current_monthly_fuel_inr - monthly_ev_cost_inr)), 0)
    annual_savings_inr = round(float(monthly_savings_inr * 12.0), 0)

    # Public dependency
    public_dep_pct = 85.0 if not home_charging_access else (15.0 if weekend_trip_km > 150.0 else 5.0)

    # Battery stress rating
    if not home_charging_access and daily_commute_km > 60:
        stress_rating = "HIGH (Frequent fast-charging)"
    elif is_heatwave and daily_commute_km > 50:
        stress_rating = "MODERATE (Thermal stress)"
    else:
        stress_rating = "LOW (Predominantly AC slow charging)"

    # Suitability verdict
    if confidence_pct >= 85.0 and home_charging_access:
        verdict = "STRONG_FIT"
        title = "Highly Recommended: Effortless EV Transition"
        reasons = [
            f"Overnight home charging covers {daily_commute_km:.0f} km daily commute with >70% reserve remaining.",
            f"Substantial financial savings of ₹{annual_savings_inr:,.0f} per year compared to current fuel expenditure.",
            "Minimal reliance on public charging plazas avoids peak-hour queue delays.",
        ]
    elif confidence_pct >= 65.0:
        verdict = "BORDERLINE"
        title = "Viable with Managed Charging Routine"
        reasons = [
            "Moderate weekly public charging dependence requires planned charging stops.",
            f"Annual fuel savings remain attractive at ₹{annual_savings_inr:,.0f}/year.",
            "Extreme summer ambient temperatures reduce range by up to 25% due to HVAC load.",
        ]
    else:
        verdict = "NOT_RECOMMENDED"
        title = "Caution: Significant Public Charging Friction"
        reasons = [
            "Lack of dedicated home charger combined with high daily mileage creates persistent queue exposure.",
            f"{weeks_at_risk} weeks flagged with potential range compromise or charging delays.",
            "Commercial fast-charging tariffs reduce operating cost advantages over hybrid alternatives.",
        ]

    return {
        "inputs": {
            "daily_commute_km": daily_commute_km,
            "weekend_trip_km": weekend_trip_km,
            "home_charging_access": home_charging_access,
            "climate_zone": climate_zone,
            "current_monthly_fuel_inr": current_monthly_fuel_inr,
            "offpeak_tariff_inr": offpeak_tariff_inr,
        },
        "outputs": {
            "ownership_confidence_pct": confidence_pct,
            "suitability_verdict": verdict,
            "verdict_title": title,
            "summary_reasons": reasons,
            "monthly_ev_energy_cost_inr": monthly_ev_cost_inr,
            "monthly_fuel_savings_inr": monthly_savings_inr,
            "annual_savings_inr": annual_savings_inr,
            "public_charging_dependency_pct": public_dep_pct,
            "battery_stress_rating": stress_rating,
            "weeks_at_risk_out_of_52": weeks_at_risk,
            "weekly_risk_timeline": weekly_risk_timeline,
        },
    }
