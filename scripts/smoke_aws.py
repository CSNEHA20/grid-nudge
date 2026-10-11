"""Smoke test script for validating deployed AWS endpoints."""
import os
import sys
import uuid

from services.client import GridNudgeClient

api = os.environ.get("API")
if not api:
    print("Error: API environment variable must be set (e.g. https://<id>.execute-api.<region>.amazonaws.com/prod)")
    sys.exit(1)

print(f"Connecting to GridNudge API: {api}")
c = GridNudgeClient(base_url=api)
run_id = f"smoke_{uuid.uuid4().hex[:6]}"

cands = [
    {
        "user_id": str(i),
        "ev": {"battery_kwh": 40.0, "current_soc": 0.55, "charger_kw": 7.4},
        "trip": {"commute_km": 30.0, "departure_step": 120},
        "context": {"archetype": "price_sensitive", "fatigue": 0.0, "last_frame": "none", "nudges_today": 0},
    }
    for i in range(20)
]

req = {
    "run_id": run_id,
    "sim_time": "2026-10-11T18:30:00",
    "grid_forecast": {"feeder_load_mw": 11.0, "capacity_mw": 12.0, "grid_stress": 0.9},
    "candidates": cands,
}

print(f"1. Submitting batch decide request (run_id: {run_id})...")
decisions = c.decide(req)
print(f"   Received {len(decisions)} decisions. Nudges selected: {sum(1 for d in decisions if d.get('allocation', {}).get('selected'))}")
assert len(decisions) == 20, f"Expected 20 decisions, got {len(decisions)}"

d0 = decisions[0]
d0_id = d0["decision_id"]
print(f"2. Fetching decision {d0_id}...")
fetched = c.get_decision(d0_id)
assert fetched is not None, f"Decision {d0_id} could not be fetched"
print(f"   Fetched successfully (fail_silent={fetched.get('fail_silent')})")

print("3. Posting outcome to /outcomes...")
outcome_resp = c.post_outcome({
    "decision_id": d0_id,
    "user_id": d0["user_id"],
    "adopted": True,
    "kwh_shifted": 8.0,
    "savings_inr": 65.0,
    "battery_stress_delta": -0.05,
    "opted_out": False,
    "realized_value": 30.0,
    "true_uplift": 0.4,
})
print(f"   Outcome response: {outcome_resp}")

print("4. Fetching metrics...")
metrics_resp = c.get_metrics(run_id)
print(f"   Metrics response: {metrics_resp}")

print("5. Explaining decision...")
explain_resp = c.explain(d0_id)
print(f"   Explain response: {explain_resp.get('summary', explain_resp)}")

print("\n--- ALL SMOKE CHECKS PASSED SUCCESSFULLY ---")
