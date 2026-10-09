"""GridNudge runner client for interacting with the decision API.

Supports both:
- HTTP mode: sends HTTP requests to deployed AWS API Gateway or local server using urllib.
- In-process direct mode: calls service handlers directly with a provided StateStore (for tests and local simulation).
"""

import json
import logging
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

from gridnudge.state import InMemoryStore, StateStore
from services import decide, decision_get, events, explain, metrics, outcomes

logger = logging.getLogger(__name__)


class GridNudgeClient:
    """Client for GridNudge decision API and evaluation pipelines."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        store: Optional[StateStore] = None,
        timeout: float = 10.0,
    ) -> None:
        """Initialize client.
        
        Args:
            base_url: HTTP base URL (e.g. 'https://xxx.execute-api.us-east-1.amazonaws.com').
                      If None, operates in direct in-process mode.
            store: StateStore for direct in-process mode (defaults to InMemoryStore).
            timeout: HTTP request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/") if base_url else None
        self.store = store if store is not None else InMemoryStore()
        self.timeout = timeout

    @property
    def is_remote(self) -> bool:
        return self.base_url is not None

    def _http_request(
        self,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Send HTTP request via urllib."""
        url = f"{self.base_url}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_bytes = resp.read()
                return json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8")
            logger.error("HTTP error %d %s: %s", err.code, err.reason, err_body)
            try:
                return json.loads(err_body)
            except Exception:
                raise RuntimeError(f"HTTP {err.code}: {err.reason} - {err_body}") from err

    def decide(self, request_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Submit candidate EV batch to /decide.
        
        Returns:
            List of DecisionRecord dictionaries.
        """
        if self.is_remote:
            resp = self._http_request("POST", "/decide", payload=request_payload)
            return resp if isinstance(resp, list) else []

        # Direct in-process invocation
        event = {"body": json.dumps(request_payload)}
        res = decide.handler(event=event, store=self.store)
        body = json.loads(res.get("body", "[]"))
        return body if isinstance(body, list) else []

    def post_outcome(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Submit realized outcome for a decision to /outcomes.
        
        Returns:
            Acknowledgement response dict.
        """
        if self.is_remote:
            return self._http_request("POST", "/outcomes", payload=outcome)

        event = {"body": json.dumps(outcome)}
        res = outcomes.handler(event=event, store=self.store)
        return json.loads(res.get("body", "{}"))

    def get_metrics(self, run_id: str) -> Dict[str, Any]:
        """Fetch timeline metrics for run_id from /metrics."""
        if self.is_remote:
            return self._http_request("GET", "/metrics", params={"run_id": run_id})

        event = {"queryStringParameters": {"run_id": run_id}}
        res = metrics.handler(event=event, store=self.store)
        return json.loads(res.get("body", "{}"))

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single DecisionRecord by ID from /decision/{id}."""
        if self.is_remote:
            return self._http_request("GET", f"/decision/{decision_id}")

        event = {"pathParameters": {"id": decision_id}}
        res = decision_get.handler(event=event, store=self.store)
        if res.get("statusCode") == 404:
            return None
        return json.loads(res.get("body", "{}"))

    def explain(self, decision_id: str) -> Dict[str, Any]:
        """Request explainability narrative for decision from /explain."""
        payload = {"decision_id": decision_id}
        if self.is_remote:
            return self._http_request("POST", "/explain", payload=payload)

        event = {"body": json.dumps(payload)}
        res = explain.handler(event=event, store=self.store)
        return json.loads(res.get("body", "{}"))

    def inject_event(self, event_type: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Inject simulation disturbance scenario via /events."""
        payload = {"event_type": event_type, "parameters": parameters or {}}
        if self.is_remote:
            return self._http_request("POST", "/events", payload=payload)

        event = {"body": json.dumps(payload)}
        res = events.handler(event=event, store=self.store)
        return json.loads(res.get("body", "{}"))
