"""Convert Python values to and from DynamoDB-safe types (floats <-> Decimal)."""
import math
from decimal import Decimal
from typing import Any


def to_dynamo(obj: Any) -> Any:
    """Recursively convert float values to Decimal for DynamoDB serialization."""
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float cannot be stored in DynamoDB: {obj}")
        return Decimal(repr(obj))
    if isinstance(obj, dict):
        return {str(k): to_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_dynamo(v) for v in obj]
    if isinstance(obj, bytes):
        return obj
    return obj


def from_dynamo(obj: Any) -> Any:
    """Recursively convert Decimal values back to int/float."""
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    if isinstance(obj, dict):
        return {k: from_dynamo(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [from_dynamo(v) for v in obj]
    return obj
