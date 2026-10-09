"""Lambda handler for GET /metrics.

Aggregates time series metrics and fleet statistics from DecisionRecords in StateStore
for dashboard visualization (hero fleet load chart, veto counts, attention budget).
"""

import collections
import logging
from typing import Any, Dict, Optional

from gridnudge.state import StateStore, get_default_store
from services.common import get_query_param, make_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for GET /metrics.
    
    Args:
        event: API Gateway HTTP API event.
        context: Lambda context object.
        store: Optional StateStore dependency injection.
        
    Returns:
        JSON response containing timeline series and aggregate counters.
    """
    try:
        run_id = get_query_param(event, "run_id")
        if not run_id:
            return make_response(400, {"error": "Missing required query parameter: 'run_id'."})

        active_store = store if store is not None else get_default_store()
        decisions = active_store.query_decisions_by_run(run_id=run_id, limit=5000)

        # Counters
        total_decisions = len(decisions)
        nudges_delivered = 0
        safety_vetoes = 0
        learned_silence_count = 0
        kwh_shifted_total = 0.0

        # Group by sim_time
        timesteps_map: Dict[str, Dict[str, Any]] = collections.defaultdict(lambda: {
            "decisions": 0,
            "nudges_delivered": 0,
            "safety_vetoes": 0,
            "learned_silence_count": 0,
            "kwh_shifted": 0.0,
            "grid_stress": 0.0,
        })

        for d in decisions:
            st = d.get("sim_time", "unknown")
            ts = timesteps_map[st]
            ts["decisions"] += 1

            safety = d.get("safety") or {}
            is_veto = bool(safety.get("vetoed") or safety.get("cedar") == "DENY")
            if is_veto:
                safety_vetoes += 1
                ts["safety_vetoes"] += 1

            alloc = d.get("allocation") or {}
            is_selected = bool(alloc.get("selected"))
            fail_silent = bool(d.get("fail_silent"))

            persuasion = d.get("persuasion") or {}
            frame = persuasion.get("frame")
            is_none_frame = frame in ("none", None)

            if is_selected and not fail_silent:
                nudges_delivered += 1
                ts["nudges_delivered"] += 1
            elif is_none_frame and not is_veto:
                learned_silence_count += 1
                ts["learned_silence_count"] += 1

            outcome = d.get("outcome") or {}
            kwh_raw = outcome.get("kwh_shifted")
            kwh = float(kwh_raw) if kwh_raw is not None else 0.0
            kwh_shifted_total += kwh
            ts["kwh_shifted"] += kwh

            grid_view = d.get("grid") or {}
            if "stress" in grid_view:
                ts["grid_stress"] = float(grid_view["stress"])

        # Construct ordered timesteps array
        sorted_times = sorted(timesteps_map.keys())
        timesteps_list = []
        for idx, t_str in enumerate(sorted_times):
            data = timesteps_map[t_str]
            timesteps_list.append({
                "step": idx,
                "sim_time": t_str,
                "nudges_delivered": data["nudges_delivered"],
                "safety_vetoes": data["safety_vetoes"],
                "learned_silence_count": data["learned_silence_count"],
                "kwh_shifted": round(data["kwh_shifted"], 2),
                "grid_stress": round(data["grid_stress"], 3),
            })

        payload = {
            "run_id": run_id,
            "provenance": "Simulation",
            "summary": {
                "total_decisions": total_decisions,
                "nudges_delivered": nudges_delivered,
                "safety_vetoes": safety_vetoes,
                "learned_silence_count": learned_silence_count,
                "kwh_shifted_total": round(kwh_shifted_total, 2),
            },
            "timesteps": timesteps_list,
        }

        return make_response(200, payload)

    except Exception as ex:
        logger.exception("Error in /metrics handler: %s", ex)
        return make_response(500, {"error": "Failed to aggregate metrics", "details": str(ex)})
