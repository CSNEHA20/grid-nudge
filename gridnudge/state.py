"""State storage interfaces and implementations for GridNudge.

Provides a swappable StateStore abstraction:
- InMemoryStore: thread-safe dictionary store for local development, tests, and simulation.
- DynamoStore: DynamoDB implementation for AWS Lambda execution.
"""

import os
import threading
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class ConcurrencyError(Exception):
    """Raised when an optimistic concurrency check fails on model or state update."""
    pass


@runtime_checkable
class StateStore(Protocol):
    """Swappable state persistence protocol for GridNudge."""

    def get_users(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """Retrieve user states by IDs. Returns map of user_id -> state dict."""
        ...

    def put_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        """Batch persist or update user states."""
        ...

    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Retrieve serialized model state by model identifier."""
        ...

    def put_model(self, model_id: str, model: Dict[str, Any], expected_version: int) -> None:
        """Persist model state with optimistic concurrency check against expected_version."""
        ...

    def put_decisions(self, records: List[Dict[str, Any]]) -> None:
        """Batch persist decision audit records."""
        ...

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve decision record by decision ID, or None if not found."""
        ...

    def query_decisions_by_run(self, run_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Query decisions by run_id, ordered by sim_time."""
        ...


class InMemoryStore:
    """Thread-safe in-memory StateStore implementation for local execution and tests."""

    def __init__(self) -> None:
        self._users: Dict[str, Dict[str, Any]] = {}
        self._models: Dict[str, Dict[str, Any]] = {}
        self._model_versions: Dict[str, int] = {}
        self._decisions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_users(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            result = {}
            for uid in ids:
                uid_str = str(uid)
                if uid_str in self._users:
                    # Return a shallow copy of stored state
                    result[uid_str] = dict(self._users[uid_str])
            return result

    def put_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        with self._lock:
            for uid, state in users.items():
                uid_str = str(uid)
                existing = self._users.get(uid_str, {})
                merged = {**existing, **state}
                self._users[uid_str] = merged

    def get_model(self, model_id: str) -> Dict[str, Any]:
        with self._lock:
            if model_id not in self._models:
                return {}
            return dict(self._models[model_id])

    def put_model(self, model_id: str, model: Dict[str, Any], expected_version: int) -> None:
        with self._lock:
            current_ver = self._model_versions.get(model_id, 0)
            if expected_version != current_ver and current_ver != 0:
                raise ConcurrencyError(
                    f"Model '{model_id}' version mismatch: expected {expected_version}, found {current_ver}"
                )
            new_version = int(model.get("version", current_ver + 1))
            self._models[model_id] = dict(model)
            self._model_versions[model_id] = new_version

    def put_decisions(self, records: List[Dict[str, Any]]) -> None:
        with self._lock:
            for rec in records:
                d_id = rec.get("decision_id")
                if d_id:
                    self._decisions[str(d_id)] = dict(rec)

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._decisions.get(str(decision_id))
            return dict(rec) if rec is not None else None

    def all_decisions(self) -> List[Dict[str, Any]]:
        """Return list of all stored decisions (useful for eval/tests)."""
        with self._lock:
            return list(self._decisions.values())

    def query_decisions_by_run(self, run_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """Query decisions matching run_id, sorted by sim_time."""
        with self._lock:
            matches = [d for d in self._decisions.values() if d.get("run_id") == run_id]
            matches.sort(key=lambda x: str(x.get("sim_time", "")))
            return [dict(d) for d in matches[:limit]]

    def clear(self) -> None:
        """Reset all in-memory store tables."""
        with self._lock:
            self._users.clear()
            self._models.clear()
            self._model_versions.clear()
            self._decisions.clear()


class DynamoStore:
    """DynamoDB StateStore adapter for AWS Lambda execution.

    Lazily connects to DynamoDB via boto3.
    """

    def __init__(
        self,
        user_table: Optional[str] = None,
        model_table: Optional[str] = None,
        decision_table: Optional[str] = None,
        dynamodb_resource: Optional[Any] = None,
    ) -> None:
        self.user_table_name = user_table or os.environ.get("USER_TABLE", "GridNudge-UserState")
        self.model_table_name = model_table or os.environ.get("MODEL_TABLE", "GridNudge-ModelState")
        self.decision_table_name = decision_table or os.environ.get("DECISION_TABLE", "GridNudge-Decisions")
        self._resource = dynamodb_resource

    def _get_resource(self) -> Any:
        if self._resource is not None:
            return self._resource
        try:
            import boto3
            endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")
            if endpoint_url:
                self._resource = boto3.resource("dynamodb", endpoint_url=endpoint_url)
            else:
                self._resource = boto3.resource("dynamodb")
            return self._resource
        except ImportError as e:
            raise RuntimeError("boto3 must be installed to use DynamoStore") from e

    def get_users(self, ids: List[str]) -> Dict[str, Dict[str, Any]]:
        db = self._get_resource()
        table = db.Table(self.user_table_name)
        result: Dict[str, Dict[str, Any]] = {}
        for uid in ids:
            try:
                resp = table.get_item(Key={"user_id": str(uid)})
                if "Item" in resp:
                    result[str(uid)] = resp["Item"]
            except Exception:
                pass
        return result

    def put_users(self, users: Dict[str, Dict[str, Any]]) -> None:
        db = self._get_resource()
        table = db.Table(self.user_table_name)
        with table.batch_writer() as batch:
            for uid, state in users.items():
                item = dict(state)
                item["user_id"] = str(uid)
                batch.put_item(Item=item)

    def get_model(self, model_id: str) -> Dict[str, Any]:
        db = self._get_resource()
        table = db.Table(self.model_table_name)
        resp = table.get_item(Key={"model_id": model_id})
        return resp.get("Item", {})

    def put_model(self, model_id: str, model: Dict[str, Any], expected_version: int) -> None:
        db = self._get_resource()
        table = db.Table(self.model_table_name)
        item = dict(model)
        item["model_id"] = model_id
        new_version = int(model.get("version", expected_version + 1))
        item["version"] = new_version

        try:
            if expected_version == 0:
                table.put_item(
                    Item=item,
                    ConditionExpression="attribute_not_exists(model_id)",
                )
            else:
                table.put_item(
                    Item=item,
                    ConditionExpression="version = :exp",
                    ExpressionAttributeValues={":exp": expected_version},
                )
        except Exception as e:
            raise ConcurrencyError(f"DynamoDB conditional check failed for model '{model_id}': {e}") from e

    def put_decisions(self, records: List[Dict[str, Any]]) -> None:
        db = self._get_resource()
        table = db.Table(self.decision_table_name)
        with table.batch_writer() as batch:
            for rec in records:
                item = dict(rec)
                batch.put_item(Item=item)

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_resource()
        table = db.Table(self.decision_table_name)
        resp = table.get_item(Key={"decision_id": str(decision_id)})
        return resp.get("Item")

    def query_decisions_by_run(self, run_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        db = self._get_resource()
        table = db.Table(self.decision_table_name)
        try:
            try:
                from boto3.dynamodb.conditions import Key
                key_cond = Key("run_id").eq(run_id)
            except (ImportError, ModuleNotFoundError):
                key_cond = f"run_id = {run_id}"

            resp = table.query(
                IndexName="by_run",
                KeyConditionExpression=key_cond,
                Limit=limit,
            )
            return resp.get("Items", [])
        except Exception:
            return []


def get_default_store() -> StateStore:
    """Return DynamoStore if AWS Lambda environment or USE_DYNAMO_STORE detected, otherwise InMemoryStore."""
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("USE_DYNAMO_STORE"):
        return DynamoStore()
    return InMemoryStore()
