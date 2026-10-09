"""Lambda handler for POST /decide.

Evaluates plugged-in EV candidates across Perception -> Planner -> Safety Gate #1 ->
Persuasion / LinTS -> Fleet Allocator -> Safety Gate #2 -> Language stages.
Emits structured metrics for CloudWatch and persists records into StateStore.
"""

import json
import logging
from typing import Any, Dict, Optional

from gridnudge.pipeline import decide_batch
from gridnudge.state import StateStore, get_default_store
from services.common import make_response, parse_body

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for POST /decide.
    
    Args:
        event: API Gateway HTTP API event or direct request payload dict.
        context: Lambda context object.
        store: Optional StateStore dependency injection for tests.
    
    Returns:
        API Gateway HTTP response containing JSON serialized DecisionRecord array.
    """
    try:
        payload = parse_body(event)
        if not payload or not isinstance(payload, dict):
            return make_response(400, {"error": "Invalid request body: expected JSON object."})

        # Required fields check per API OpenAPI schema
        if "candidates" not in payload:
            return make_response(400, {"error": "Missing required field: 'candidates'."})

        # Inject default store if not provided
        active_store = store if store is not None else get_default_store()

        # Run pipeline decision orchestrator
        decisions = decide_batch(
            request=payload,
            store=active_store,
            render_llm=False,
        )

        records_dump = [d.model_dump(mode="json") for d in decisions]

        # Calculate structured observability metrics for CloudWatch
        veto_count = sum(1 for d in decisions if d.safety and (d.safety.vetoed or d.safety.cedar == "DENY"))
        fail_silent_count = sum(1 for d in decisions if d.fail_silent)
        nudges_sent = sum(1 for d in decisions if d.allocation and d.allocation.selected and not d.fail_silent)

        logger.info(
            json.dumps({
                "metric_type": "decide_batch",
                "run_id": payload.get("run_id"),
                "total_candidates": len(payload.get("candidates", [])),
                "decisions_count": len(decisions),
                "veto_count": veto_count,
                "fail_silent_count": fail_silent_count,
                "nudges_sent": nudges_sent,
            })
        )

        return make_response(200, records_dump)

    except Exception as ex:
        logger.exception("Unexpected error in /decide handler: %s", ex)
        return make_response(500, {"error": "Internal decision pipeline failure", "details": str(ex)})
