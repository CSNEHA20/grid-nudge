"""Lambda handler for POST /events.

Allows injecting disturbance scenario events into the simulation
(heatwave, solar_drop, station_outage, tariff_change).
"""

import logging
from typing import Any, Dict, Optional

from services.common import make_response, parse_body

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VALID_EVENTS = {"heatwave", "solar_drop", "station_outage", "tariff_change"}


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[Any] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for POST /events.
    
    Args:
        event: API Gateway HTTP API event or direct payload dict.
        context: Lambda context object.
        store: Optional StateStore dependency injection.
        
    Returns:
        HTTP response confirming event application.
    """
    try:
        payload = parse_body(event)
        event_type = payload.get("event_type")
        if not event_type or event_type not in VALID_EVENTS:
            return make_response(400, {
                "error": f"Invalid or missing event_type. Must be one of {sorted(VALID_EVENTS)}."
            })

        parameters = payload.get("parameters", {})
        logger.info("Simulation event injected: %s with params %s", event_type, parameters)

        return make_response(200, {
            "status": "applied",
            "event_type": event_type,
            "parameters": parameters,
        })

    except Exception as ex:
        logger.exception("Error in /events handler: %s", ex)
        return make_response(500, {"error": "Failed to apply event", "details": str(ex)})
