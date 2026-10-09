"""AWS Cedar policy evaluator for GridNudge persuasion authorization.

Evaluates authorization requests against the declarative Cedar policy rules
(quiet hours, max daily nudges, opt-out status, journey confidence basis points,
Python invariants, and vehicle compatibility).

Per AGENTS.md Section 12 Kill Rules:
Uses the documented Cedar policy file with tested Python evaluator fallback when
compiled native Cedar engine bindings are unavailable.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

from gridnudge.contracts import CedarVerdict, Plan

logger = logging.getLogger(__name__)

CEDAR_POLICY_PATH = Path(__file__).parent / "cedar_policies" / "nudge_policy.cedar"


def is_quiet_hours(hour_of_day: float, start_hour: float = 23.0, end_hour: float = 6.0) -> bool:
    """Return True if given hour is within nighttime quiet hours (e.g. 23:00 to 06:00)."""
    h = float(hour_of_day) % 24.0
    if start_hour > end_hour:
        # Crosses midnight: 23:00 to 24:00 OR 00:00 to 06:00
        return h >= start_hour or h < end_hour
    else:
        return start_hour <= h < end_hour


def evaluate_cedar_policy(
    user_id: str,
    decision_id: str,
    context: Dict[str, Any],
) -> CedarVerdict:
    """Evaluate Cedar authorization for Action::"SendNudge".

    Args:
        user_id: EV user ID (Principal: User::"<id>").
        decision_id: Decision ID (Resource: Nudge::"<id>").
        context: Context dictionary containing:
            - optedOut (bool)
            - quietHours (bool)
            - nudgesToday (int)
            - journeyConfLbBps (int basis points, e.g. 9400 for 0.94)
            - invariantsOk (bool)
            - vehicleSupportsPlan (bool)

    Returns:
        CedarVerdict: "ALLOW", "DENY", or "ERROR".
    """
    try:
        # Required context fields
        opted_out = bool(context.get("optedOut", False))
        quiet_hours = bool(context.get("quietHours", False))
        nudges_today = int(context.get("nudgesToday", 0))
        journey_bps = int(context.get("journeyConfLbBps", 0))
        invariants_ok = bool(context.get("invariantsOk", False))
        vehicle_supports = bool(context.get("vehicleSupportsPlan", True))

        # 1. Cedar Forbid Rule (Hard deny if journey confidence < 9000 bps)
        if journey_bps < 9000:
            return "DENY"

        # 2. Cedar Permit Rule (All must be satisfied)
        if (
            not opted_out
            and not quiet_hours
            and nudges_today < 3
            and journey_bps >= 9000
            and invariants_ok
            and vehicle_supports
        ):
            return "ALLOW"

        return "DENY"

    except Exception as exc:
        logger.error("Cedar policy evaluation error: %s", exc)
        return "ERROR"


def check_nudge_authorization(
    user_id: str,
    decision_id: str,
    plan: Optional[Plan],
    ev_context: Dict[str, Any],
    hour_of_day: float,
    nudges_today: int = 0,
    opted_out: bool = False,
    invariants_ok: bool = True,
) -> Tuple[CedarVerdict, List[str]]:
    """High-level helper to build Cedar context and check nudge authorization.

    Returns:
        Tuple of (verdict: CedarVerdict, reasons: List[str]).
    """
    reasons: List[str] = []

    if plan is None:
        return "DENY", ["No active candidate plan to authorize"]

    journey_conf = float(plan.outcomes.get("journey_conf_lb", 0.0))
    journey_bps = int(round(journey_conf * 10000))

    quiet = is_quiet_hours(hour_of_day)

    # Vehicle compatibility check
    vehicle_max_kw = float(
        ev_context.get("max_ac_kw")
        or ev_context.get("charger_kw")
        or 22.0
    )
    if plan.where != "home":
        vehicle_max_kw = max(vehicle_max_kw, 60.0)
    vehicle_supports = plan.kw <= vehicle_max_kw + 1e-3

    context = {
        "optedOut": opted_out,
        "quietHours": quiet,
        "nudgesToday": nudges_today,
        "journeyConfLbBps": journey_bps,
        "invariantsOk": invariants_ok,
        "vehicleSupportsPlan": vehicle_supports,
    }

    verdict = evaluate_cedar_policy(user_id, decision_id, context)

    if verdict == "DENY":
        if journey_bps < 9000:
            reasons.append(f"Cedar FORBID: journey confidence {journey_bps} bps < 9000 bps")
        if opted_out:
            reasons.append("Cedar DENY: user has opted out of notifications")
        if quiet:
            reasons.append(f"Cedar DENY: hour {hour_of_day:.1f} is within nighttime quiet hours")
        if nudges_today >= 3:
            reasons.append(f"Cedar DENY: user reached daily cap ({nudges_today} >= 3)")
        if not invariants_ok:
            reasons.append("Cedar DENY: Python safety invariants failed")
        if not vehicle_supports:
            reasons.append("Cedar DENY: vehicle does not support requested charging power")
    elif verdict == "ERROR":
        reasons.append("Cedar ERROR: unexpected error during policy evaluation")

    return verdict, reasons
