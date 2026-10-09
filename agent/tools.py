"""Operator copilot tools for GridNudge.

Provides read-only operational inquiry tools for auditing decisions, explaining safety vetoes,
comparing fleet policies, and validating injected disturbance scenarios.

Per GEMINI.md Section 13:
The copilot is read-only with respect to decisions.
It explains the system. It does not decide or modify safety thresholds.
All explanations strictly cite decision IDs and approved factual values.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

VALID_SCENARIOS = ["heatwave", "solar_drop", "station_outage", "tariff_change"]


def get_decision(
    decision_id: str,
    store: Optional[Any] = None,
    fixtures_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve an auditable DecisionRecord by ID.

    Args:
        decision_id: Unique decision identifier (e.g. 'd_002_safety_veto').
        store: Optional StateStore instance.
        fixtures_path: Optional path to sample decisions fixtures.

    Returns:
        DecisionRecord dictionary or error dict if not found.
    """
    # 1. Query store if provided
    if store is not None and hasattr(store, "get_decision"):
        rec = store.get_decision(decision_id)
        if rec:
            return rec

    # 2. Fallback to sample fixtures for demo and inspection
    p = Path(fixtures_path) if fixtures_path else Path(__file__).resolve().parent.parent / "fixtures" / "decisions.sample.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                decisions = json.load(f)
            for d in decisions:
                if d.get("decision_id") == decision_id:
                    return d
        except Exception:
            pass

    return {
        "decision_id": decision_id,
        "error": f"Decision {decision_id} not found in store or fixtures.",
    }


def explain_veto(
    decision_id: str,
    store: Optional[Any] = None,
) -> Dict[str, Any]:
    """Explain why a candidate charging plan was vetoed by the safety gate.

    Returns:
        Structured explanation citing decision ID, Cedar verdict, journey confidence,
        and human-readable veto reasons.
    """
    decision = get_decision(decision_id, store=store)
    if decision.get("error"):
        return {"decision_id": decision_id, "explanation": decision["error"]}

    safety_info = decision.get("safety", {})
    vetoed_reasons: List[str] = safety_info.get("vetoed", [])
    cedar_verdict = safety_info.get("cedar", "UNKNOWN")
    invariants_ok = safety_info.get("invariants_ok", True)

    journey = decision.get("journey", {})
    journey_conf = journey.get("p_arrive_above_reserve")

    if not vetoed_reasons and cedar_verdict == "ALLOW":
        return {
            "decision_id": decision_id,
            "was_vetoed": False,
            "explanation": f"Decision {decision_id} was NOT vetoed. Safety checks passed with Cedar ALLOW.",
        }

    # Construct auditable explanation citing facts
    points = []
    if not invariants_ok:
        points.append("Python physical invariants failed.")
    if cedar_verdict == "DENY":
        points.append("AWS Cedar policy returned DENY.")
    if journey_conf is not None:
        points.append(f"Journey confidence was {journey_conf * 100:.1f}%.")

    for r in vetoed_reasons:
        points.append(f"Veto: {r}")

    explanation_text = (
        f"Decision {decision_id} was safety-gated before persuasion could occur. "
        f"Cedar verdict: {cedar_verdict}. "
        f"Details: {'; '.join(points)}"
    )

    return {
        "decision_id": decision_id,
        "was_vetoed": True,
        "cedar_verdict": cedar_verdict,
        "invariants_ok": invariants_ok,
        "vetoed_reasons": vetoed_reasons,
        "explanation": explanation_text,
    }


def compare_policies(
    policy_a_metrics: Dict[str, Any],
    policy_b_metrics: Dict[str, Any],
    policy_a_name: str = "B0 Uncontrolled",
    policy_b_name: str = "B4 GridNudge",
) -> Dict[str, Any]:
    """Compare performance metrics between baseline and GridNudge policies.

    Args:
        policy_a_metrics: Baseline metrics (e.g. peak_load_mw, shifted_kwh, nudges_sent).
        policy_b_metrics: Comparison policy metrics.
        policy_a_name: Name of policy A.
        policy_b_name: Name of policy B.

    Returns:
        Comparison summary dictionary with delta statistics.
    """
    peak_a = float(policy_a_metrics.get("peak_load_mw", 0.0))
    peak_b = float(policy_b_metrics.get("peak_load_mw", 0.0))
    peak_delta_mw = round(peak_b - peak_a, 2)
    peak_reduction_pct = round(((peak_a - peak_b) / max(0.01, peak_a)) * 100.0, 2) if peak_a > 0 else 0.0

    kwh_a = float(policy_a_metrics.get("shifted_kwh", 0.0))
    kwh_b = float(policy_b_metrics.get("shifted_kwh", 0.0))
    shifted_delta = round(kwh_b - kwh_a, 2)

    nudges_a = int(policy_a_metrics.get("nudges_per_user", 0))
    nudges_b = int(policy_b_metrics.get("nudges_per_user", 0))

    return {
        "policy_a": policy_a_name,
        "policy_b": policy_b_name,
        "peak_reduction_mw": abs(peak_delta_mw) if peak_delta_mw < 0 else 0.0,
        "peak_reduction_pct": peak_reduction_pct,
        "additional_shifted_kwh": max(0.0, shifted_delta),
        "nudges_per_user_a": nudges_a,
        "nudges_per_user_b": nudges_b,
        "summary": (
            f"{policy_b_name} reduces peak load by {peak_reduction_pct}% "
            f"({abs(peak_delta_mw)} MW) and shifts {shifted_delta} kWh compared to {policy_a_name}."
        ),
    }


def inject_scenario(
    scenario_type: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate and configure an environmental scenario injection.

    Supported scenarios:
    - heatwave: Ambient temperature rise (+8 °C) raising HVAC load.
    - solar_drop: Sudden solar PV generation reduction (-40%).
    - station_outage: Selected public charging hubs go offline.
    - tariff_change: Evening peak surcharge multiplication.

    Returns:
        Validated scenario configuration dictionary.
    """
    s_type = scenario_type.lower().strip()
    if s_type not in VALID_SCENARIOS:
        return {
            "status": "error",
            "message": f"Invalid scenario type '{scenario_type}'. Supported: {VALID_SCENARIOS}",
        }

    p = params or {}
    config: Dict[str, Any] = {"scenario": s_type, "enabled": True}

    if s_type == "heatwave":
        config["temp_rise_c"] = float(p.get("temp_rise_c", 8.0))
        config["hvac_multiplier"] = float(p.get("hvac_multiplier", 1.45))
    elif s_type == "solar_drop":
        config["solar_reduction_factor"] = float(p.get("solar_reduction_factor", 0.60))
    elif s_type == "station_outage":
        config["offline_station_ids"] = list(p.get("offline_station_ids", [1, 2]))
    elif s_type == "tariff_change":
        config["peak_tariff_multiplier"] = float(p.get("peak_tariff_multiplier", 1.50))

    return {
        "status": "validated",
        "scenario_config": config,
        "message": f"Scenario '{s_type}' validated and ready for simulation injection.",
    }
