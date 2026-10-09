"""Lambda handler for SQS FIFO reward update processing.

Processes batched outcomes from SQS FIFO queue with reserved concurrency = 1 (single writer).
Updates LinTS model posterior in StateStore and writes audit logs to S3.
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from gridnudge.pipeline import process_outcomes
from gridnudge.state import StateStore, get_default_store

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(
    event: Dict[str, Any],
    context: Optional[Any] = None,
    store: Optional[StateStore] = None,
    s3_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Lambda entrypoint triggered by SQS FIFO Queue.
    
    Args:
        event: SQS event dict containing Records, or direct list/dict payload for tests.
        context: Lambda context object.
        store: Optional StateStore dependency injection for tests.
        s3_client: Optional boto3 S3 client dependency injection.
        
    Returns:
        Summary dict of processed reward updates.
    """
    try:
        outcomes: List[Dict[str, Any]] = []

        # 1. Parse records from SQS event
        if isinstance(event, dict) and "Records" in event:
            for rec in event.get("Records", []):
                raw_body = rec.get("body", "")
                if isinstance(raw_body, str):
                    try:
                        outcomes.append(json.loads(raw_body))
                    except json.JSONDecodeError:
                        logger.warning("Failed to decode SQS message body: %s", raw_body)
                elif isinstance(raw_body, dict):
                    outcomes.append(raw_body)
        elif isinstance(event, list):
            outcomes = [item for item in event if isinstance(item, dict)]
        elif isinstance(event, dict):
            outcomes = [event]

        if not outcomes:
            logger.info("No outcomes to process in event.")
            return {"status": "ok", "processed": 0}

        active_store = store if store is not None else get_default_store()

        # 2. Process outcomes and update LinTS posterior
        result = process_outcomes(outcomes=outcomes, store=active_store)
        logger.info("Reward update executed: %s", result)

        # 3. Optional audit log write to S3
        bucket_name = os.environ.get("LOG_BUCKET")
        if bucket_name or s3_client is not None:
            try:
                if s3_client is None:
                    import boto3
                    s3_client = boto3.client("s3")
                key = f"reward_updates/update_{int(time.time() * 1000)}.json"
                audit_payload = {
                    "timestamp": time.time(),
                    "outcomes_count": len(outcomes),
                    "result": result,
                }
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=key,
                    Body=json.dumps(audit_payload),
                    ContentType="application/json",
                )
                logger.info("Audit log written to s3://%s/%s", bucket_name, key)
            except Exception as s3_err:
                logger.warning("Could not write S3 audit log (%s)", s3_err)

        return {"status": "ok", "processed": len(outcomes), "metrics": result}

    except Exception as ex:
        logger.exception("Error in reward_update handler: %s", ex)
        raise
