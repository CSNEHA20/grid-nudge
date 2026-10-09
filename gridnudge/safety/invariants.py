"""Python safety invariants for GridNudge.

Safety Filter #1 enforces hard physical and operational constraints BEFORE the bandit
sees candidate plans. The bandit is never allowed to trade safety for reward.
"""

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from gridnudge.contracts import Plan


@dataclass
class SafetyLimits:
    """Configured thresholds for safety invariants."""

    min_journey_conf: float = 0.90
    reserve_soc: float = 0.10
    max_battery_soc: float = 1.00
    min_battery_soc: float = 0.00
    max_nudges_per_day: int = 3
    rebound_peak_threshold_pct: float = 0.98


def load_safety_limits(config_path: Optional[str] = None) -> SafetyLimits:
    """Load safety limits from config/safety.yaml or return canonical defaults."""
    default_limits = SafetyLimits()
    if config_path is None:
        p = Path(__file__).resolve().parent.parent.parent / "config" / "safety.yaml"
    else:
        p = Path(config_path)

    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return SafetyLimits(
                min_journey_conf=float(data.get("journey_confidence_lower_bound", 0.90)),
                reserve_soc=float(data.get("reserve_soc", 0.10)),
                max_battery_soc=float(data.get("max_battery_soc", 1.00)),
                min_battery_soc=float(data.get("min_battery_soc", 0.00)),
                max_nudges_per_day=int(data.get("max_nudges_per_user_per_day", 3)),
                rebound_peak_threshold_pct=float(data.get("rebound_peak_threshold_pct", 0.98)),
            )
        except Exception:
            return default_limits
    return default_limits


DEFAULT_LIMITS = load_safety_limits()


def validate_plan_invariants(
    plan: Plan,
    ev_context: Dict[str, Any],
    limits: Optional[SafetyLimits] = None,
) -> Tuple[bool, List[str]]:
    """Validate a candidate plan against all non-negotiable Python invariants.

    Returns:
        Tuple of (is_safe: bool, veto_reasons: List[str]).
    """
    lim = limits or DEFAULT_LIMITS
    reasons: List[str] = []

    outcomes = plan.outcomes

    # 1. Journey confidence invariant (AGENTS.md Section 3.6 & 9)
    journey_conf = outcomes.get("journey_conf_lb")
    if journey_conf is None or math.isnan(journey_conf) or math.isinf(journey_conf):
        reasons.append(f"{plan.plan_id}: invalid journey_conf_lb (NaN or missing)")
    elif journey_conf < lim.min_journey_conf:
        reasons.append(
            f"{plan.plan_id}: journey_conf_lb {journey_conf:.2f} < threshold {lim.min_journey_conf:.2f}"
        )

    # 2. Arrival SOC Q10 must be >= reserve SOC if provided
    arrival_soc_q10 = outcomes.get("arrival_soc_q10")
    if arrival_soc_q10 is not None:
        if math.isnan(arrival_soc_q10) or arrival_soc_q10 < lim.reserve_soc:
            reasons.append(
                f"{plan.plan_id}: arrival_soc_q10 {arrival_soc_q10:.2f} < reserve {lim.reserve_soc:.2f}"
            )

    # 3. Vehicle power limit invariant
    # Vehicle maximum supported AC or DC kW
    vehicle_max_kw = float(
        ev_context.get("max_ac_kw")
        or ev_context.get("charger_kw")
        or 22.0
    )
    # If at DC public station, allow up to vehicle DC max or station connector limit
    if plan.where != "home":
        vehicle_max_kw = max(vehicle_max_kw, 60.0)

    if plan.kw > vehicle_max_kw + 1e-3:
        reasons.append(
            f"{plan.plan_id}: requested power {plan.kw:.1f} kW exceeds vehicle limit {vehicle_max_kw:.1f} kW"
        )

    # 4. Numerical sanity checks
    if plan.kw < 0.0 or math.isnan(plan.kw) or math.isinf(plan.kw):
        reasons.append(f"{plan.plan_id}: invalid negative or non-finite power {plan.kw}")

    wait_min = outcomes.get("wait_min", 0.0)
    if wait_min < 0.0 or math.isnan(wait_min):
        reasons.append(f"{plan.plan_id}: invalid negative queue wait {wait_min}")

    # 5. Grid rebound peak invariant
    if outcomes.get("creates_new_peak", False):
        reasons.append(f"{plan.plan_id}: plan would exceed feeder capacity in its slot")

    is_safe = len(reasons) == 0
    return is_safe, reasons


def filter_safe_plans(
    plans: List[Plan],
    ev_context: Dict[str, Any],
    limits: Optional[SafetyLimits] = None,
) -> Tuple[List[Plan], List[str]]:
    """Safety Filter #1: Remove unsafe plans before persuasion/bandit.

    Args:
        plans: Candidate plans from the planner.
        ev_context: EV state and specifications.
        limits: Configured safety limits.

    Returns:
        Tuple of (safe_plans, vetoed_reasons).
    """
    safe_plans: List[Plan] = []
    all_vetoed_reasons: List[str] = []

    for plan in plans:
        is_safe, reasons = validate_plan_invariants(plan, ev_context, limits)
        if is_safe:
            safe_plans.append(plan)
        else:
            all_vetoed_reasons.extend(reasons)

    return safe_plans, all_vetoed_reasons
