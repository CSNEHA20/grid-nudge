"""Lambda handler for GET /decision/{id}.

Retrieves a single auditable DecisionRecord by ID from StateStore.
"""

import logging
from typing import Any, Dict, Optional

from gridnudge.state import StateStore, get_default_store
from services.common import get_path_param, get_query_param, make_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for GET /decision/{id}.
    
    Args:
        event: API Gateway HTTP API event.
        context: Lambda context object.
        store: Optional StateStore dependency injection.
        
    Returns:
        JSON response with DecisionRecord or 404 if not found.
    """
    try:
        decision_id = get_path_param(event, "id") or get_query_param(event, "id")
        if not decision_id:
            return make_response(400, {"error": "Missing required path parameter 'id'."})

        active_store = store if store is not None else get_default_store()
        rec = active_store.get_decision(decision_id)

        if rec is None:
            return make_response(404, {
                "error": "Decision not found",
                "decision_id": decision_id,
            })

        return make_response(200, rec)

    except Exception as ex:
        logger.exception("Error in /decision/{id} handler: %s", ex)
        return make_response(500, {"error": "Internal error fetching decision", "details": str(ex)})
