"""Lambda handler for POST /outcomes.

Ingests realized user charging outcomes from the simulator.
In AWS production mode: enqueues to SQS FIFO reward queue for single-writer processing.
In fallback / local test mode: processes synchronously via process_outcomes.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from gridnudge.pipeline import process_outcomes
from gridnudge.state import StateStore, get_default_store
from services.common import make_response, parse_body

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
    sqs_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint for POST /outcomes.
    
    Args:
        event: API Gateway HTTP API event or direct payload dict.
        context: Lambda context object.
        store: Optional StateStore instance for fallback synchronous processing.
        sqs_client: Optional boto3 SQS client dependency injection for tests.
        
    Returns:
        HTTP response with 202 Accepted.
    """
    try:
        payload = parse_body(event)
        if not payload or not isinstance(payload, dict):
            return make_response(400, {"error": "Invalid request body: expected JSON object."})

        decision_id = payload.get("decision_id")
        run_id = payload.get("run_id")

        if not decision_id:
            return make_response(400, {"error": "Missing required field: 'decision_id'."})

        queue_url = os.environ.get("REWARD_QUEUE_URL")

        # 1. Enqueue to SQS FIFO if queue URL is configured or mock SQS client is injected
        if queue_url or sqs_client is not None:
            try:
                if sqs_client is None:
                    import boto3
                    sqs_client = boto3.client("sqs")

                group_id = str(run_id or "default_group")
                dedup_id = str(decision_id)

                sqs_client.send_message(
                    QueueUrl=queue_url,
                    MessageBody=json.dumps(payload),
                    MessageGroupId=group_id,
                    MessageDeduplicationId=dedup_id,
                )

                logger.info("Enqueued outcome for decision %s to SQS FIFO", decision_id)
                return make_response(202, {
                    "status": "accepted",
                    "mode": "enqueued",
                    "decision_id": decision_id,
                })
            except Exception as sqs_err:
                logger.warning("Failed to enqueue to SQS (%s); falling back to synchronous processing", sqs_err)

        # 2. Fallback / Kill-rule: Process synchronously inside /outcomes
        active_store = store if store is not None else get_default_store()
        res = process_outcomes([payload], store=active_store)

        logger.info("Processed outcome synchronously for decision %s: %s", decision_id, res)
        return make_response(202, {
            "status": "accepted",
            "mode": "synchronous",
            "decision_id": decision_id,
            "metrics": res,
        })

    except Exception as ex:
        logger.exception("Unexpected error in /outcomes handler: %s", ex)
        return make_response(500, {"error": "Failed to process outcome", "details": str(ex)})
