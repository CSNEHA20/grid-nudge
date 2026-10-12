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


def create_client_policy(
    client: GridNudgeClient,
    run_id: str = "b4_aws",
) -> Any:
    """Create a digital twin policy callback powered by GridNudgeClient (remote API or in-process)."""

    def policy_fn(world: Any) -> List[Dict[str, Any]]:
        closed_outcomes = world.pop_outcomes()
        for o in closed_outcomes:
            client.post_outcome(o)

        candidates = world.candidates()
        if not candidates:
            return []

        grid_st = world.grid_state()
        if not grid_st.get("is_peak_window", False):
            return []

        cand_payload = []
        for c in candidates:
            departure_step = c.get("departure_step")
            hours_dep = (
                max(1.0, (departure_step - world.current_step) * (world.step_minutes / 60.0))
                if departure_step is not None
                else 8.0
            )
            soc = float(c["soc"])
            target_soc = float(c.get("target_soc", 0.90))
            batt_kwh = float(c["battery_kwh"])
            charger_kw = float(c["charger_kw"])
            energy_needed = max(0.0, (target_soc - soc) * batt_kwh)
            overlap_start = max(world.hour_of_day, 18.0)
            overlap_end = min(world.hour_of_day + hours_dep, 22.0)
            overlap_hours = max(0.0, overlap_end - overlap_start)
            shiftable_peak_kwh = max(0.0, min(energy_needed, charger_kw * overlap_hours))
            overlaps_peak = 1.0 if (overlap_hours > 0.0 and shiftable_peak_kwh > 0.0) else 0.0

            cand_payload.append({
                "user_id": c["user_id"],
                "ev": {
                    "battery_kwh": c["battery_kwh"],
                    "current_soc": c["soc"],
                    "charger_kw": c["charger_kw"],
                    "target_soc": target_soc,
                    "shiftable_peak_kwh": round(shiftable_peak_kwh, 3),
                    "overlaps_peak": overlaps_peak,
                },
                "trip": {
                    "commute_km": float(c.get("commute_km", 38.0)),
                    "departure_step": departure_step,
                    "hours_until_departure": hours_dep,
                },
                "context": {
                    "archetype": c["archetype"],
                    "fatigue": c["fatigue"],
                    "nudges_today": c.get("nudges_today", 0),
                    "last_frame": c.get("last_frame", "none"),
                    "shiftable_peak_kwh": round(shiftable_peak_kwh, 3),
                    "overlaps_peak": overlaps_peak,
                },
            })

        req = {
            "run_id": run_id,
            "sim_time": world.sim_time.isoformat(),
            "grid_forecast": {
                "feeder_load_mw": grid_st.get("feeder_load_mw", 8.0),
                "capacity_mw": grid_st.get("feeder_capacity_mw", 12.0),
                "grid_stress": grid_st.get("grid_stress", 0.7),
                "ambient_temp_c": getattr(world, "ambient_temp_c", 30.0),
            },
            "candidates": cand_payload,
        }

        decisions = client.decide(req)
        interventions = []
        for d in decisions:
            alloc = d.get("allocation", {})
            if alloc.get("selected") and not d.get("fail_silent"):
                chosen_p = d.get("persuasion", {}).get("chosen_plan")
                plan_obj = next((p for p in d.get("plans", []) if p.get("plan_id") == chosen_p), None)
                if plan_obj:
                    interventions.append({
                        "decision_id": d["decision_id"],
                        "user_id": d["user_id"],
                        "plan": plan_obj,
                        "frame": d.get("persuasion", {}).get("frame"),
                        "savings_inr": plan_obj.get("outcomes", {}).get("cost_saving_inr", 0.0),
                        "delay_hours": plan_obj.get("outcomes", {}).get("delay_hours", 0.0),
                    })
        return interventions

    return policy_fn
