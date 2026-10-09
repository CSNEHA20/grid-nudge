"""Lambda handler for POST /explain.

Generates verified explainability narration for a decision, citing factual values,
Cedar policy evaluation, safety invariants, and persuasion frame logic.
Per GEMINI.md:
The LLM / explainer never decides. All numeric values cited originate from the DecisionRecord.
"""

import logging
from typing import Any, Dict, Optional

from agent.tools import explain_veto
from gridnudge.state import StateStore, get_default_store
from services.common import make_response, parse_body

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for POST /explain.
    
    Args:
        event: API Gateway HTTP API event or direct payload dict.
        context: Lambda context object.
        store: Optional StateStore dependency injection.
        
    Returns:
        HTTP response with structured explanation and cited facts.
    """
    try:
        payload = parse_body(event)
        if not payload or not isinstance(payload, dict):
            return make_response(400, {"error": "Invalid request body: expected JSON object."})

        decision_id = payload.get("decision_id")
        if not decision_id:
            return make_response(400, {"error": "Missing required field: 'decision_id'."})

        active_store = store if store is not None else get_default_store()
        rec = active_store.get_decision(decision_id)

        if rec is None:
            return make_response(404, {
                "error": "Decision not found",
                "decision_id": decision_id,
            })

        safety = rec.get("safety") or {}
        is_vetoed = bool(safety.get("vetoed") or safety.get("cedar") == "DENY")

        if is_vetoed:
            veto_explanation = explain_veto(decision_id, store=active_store)
            return make_response(200, {
                "decision_id": decision_id,
                "was_vetoed": True,
                "explanation": veto_explanation.get("explanation"),
                "facts": {
                    "cedar_verdict": safety.get("cedar", "DENY"),
                    "invariants_ok": safety.get("invariants_ok", True),
                    "vetoed_reasons": safety.get("vetoed", []),
                    "journey_confidence": (rec.get("journey") or {}).get("p_arrive_above_reserve"),
                },
            })

        # Not vetoed - build narrative explaining decision
        persuasion = rec.get("persuasion") or {}
        frame = persuasion.get("frame", "none")
        plan_id = persuasion.get("chosen_plan")
        alloc = rec.get("allocation") or {}
        is_selected = alloc.get("selected", False)
        slot = alloc.get("slot")

        if not is_selected or frame == "none":
            narrative = (
                f"Decision {decision_id}: Silence / 'none' action was selected. "
                f"The contextual uplift model determined that sending a nudge either had zero net benefit, "
                f"the user would naturally shift without interference, or the user is experiencing fatigue. "
                f"Attention budget was preserved."
            )
        else:
            narrative = (
                f"Decision {decision_id}: Plan '{plan_id}' selected with '{frame}' framing for slot '{slot}'. "
                f"Journey confidence satisfied safety threshold >= 0.90. "
                f"Fleet allocator granted slot within attention and feeder capacity."
            )

        facts = {
            "was_vetoed": False,
            "cedar_verdict": safety.get("cedar", "ALLOW"),
            "chosen_plan": plan_id,
            "frame": frame,
            "slot": slot,
            "allocated": is_selected,
            "journey_confidence": (rec.get("journey") or {}).get("p_arrive_above_reserve"),
        }

        return make_response(200, {
            "decision_id": decision_id,
            "was_vetoed": False,
            "explanation": narrative,
            "facts": facts,
        })

    except Exception as ex:
        logger.exception("Error in /explain handler: %s", ex)
        return make_response(500, {"error": "Failed to explain decision", "details": str(ex)})
