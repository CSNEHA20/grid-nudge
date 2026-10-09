"""Common HTTP utilities and parsing helpers for GridNudge Lambda services."""

import base64
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Parse JSON body from API Gateway (v1 or v2) event.
    
    If event is already the payload dictionary or contains raw body, extracts clean dict.
    """
    if not isinstance(event, dict):
        return {}
        
    if "body" not in event:
        # Direct invocation with payload as event
        return event

    body = event.get("body")
    if body is None:
        return {}

    if isinstance(body, dict):
        return body

    if isinstance(body, str):
        if event.get("isBase64Encoded", False):
            try:
                body = base64.b64decode(body).decode("utf-8")
            except Exception as ex:
                logger.warning("Base64 decode error: %s", ex)
                return {}
        try:
            return json.loads(body)
        except json.JSONDecodeError as ex:
            logger.warning("JSON decode error: %s", ex)
            return {}

    return {}


def get_query_param(event: Dict[str, Any], param_name: str, default: Optional[str] = None) -> Optional[str]:
    """Extract query parameter from event."""
    if not isinstance(event, dict):
        return default
    params = event.get("queryStringParameters") or {}
    return params.get(param_name, default)


def get_path_param(event: Dict[str, Any], param_name: str, default: Optional[str] = None) -> Optional[str]:
    """Extract path parameter from event."""
    if not isinstance(event, dict):
        return default
    params = event.get("pathParameters") or {}
    return params.get(param_name, default)


def make_response(status_code: int, payload: Any) -> Dict[str, Any]:
    """Build API Gateway standard HTTP response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(payload, default=str),
    }
