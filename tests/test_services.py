"""Tests for GridNudge AWS Lambda services, client, and state store adapters (M10)."""

import json
from unittest.mock import MagicMock
import pytest

from gridnudge.state import DynamoStore, InMemoryStore, get_default_store
from services import (
    GridNudgeClient,
    decide,
    decision_get,
    events,
    explain,
    metrics,
    outcomes,
    reward_update,
)


@pytest.fixture
def sample_decide_payload():
    return {
        "run_id": "test_run_101",
        "sim_time": "2026-10-10T18:00:00+05:30",
        "grid_forecast": {
            "feeder_load_mw": 8.0,
            "capacity_mw": 12.0,
            "grid_stress": 0.67,
            "ambient_temp_c": 32.0,
        },
        "candidates": [
            {
                "user_id": "u_service_01",
                "ev": {
                    "battery_kwh": 60.0,
                    "current_soc": 0.35,
                    "charger_kw": 7.4,
                },
                "trip": {
                    "commute_km": 28.0,
                    "departure_step": 36,
                },
                "context": {
                    "archetype": "commuter",
                    "fatigue": 0.0,
                    "last_frame": "none",
                },
            },
            {
                "user_id": "u_service_02",
                "ev": {
                    "battery_kwh": 40.0,
                    "current_soc": 0.85,
                    "charger_kw": 3.3,
                },
                "trip": {
                    "commute_km": 15.0,
                    "departure_step": 40,
                },
                "context": {
                    "archetype": "night_owl",
                    "fatigue": 0.2,
                    "last_frame": "cost",
                },
            },
        ],
    }


class TestDecideHandler:
    def test_decide_valid_request(self, sample_decide_payload):
        store = InMemoryStore()
        event = {"body": json.dumps(sample_decide_payload)}
        resp = decide.handler(event, store=store)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert isinstance(body, list)
        assert len(body) == 2
        for rec in body:
            assert "decision_id" in rec
            assert "safety" in rec
            assert "journey" in rec
            assert "battery" in rec

        # Decisions should be persisted in store
        assert len(store.all_decisions()) == 2

    def test_decide_missing_candidates(self):
        store = InMemoryStore()
        event = {"body": json.dumps({"run_id": "r1"})}
        resp = decide.handler(event, store=store)
        assert resp["statusCode"] == 400

    def test_decide_invalid_json(self):
        store = InMemoryStore()
        event = {"body": "not_json"}
        resp = decide.handler(event, store=store)
        assert resp["statusCode"] == 400


class TestOutcomesHandler:
    def test_outcomes_synchronous_fallback(self, sample_decide_payload):
        store = InMemoryStore()
        # First generate a decision
        decide.handler({"body": json.dumps(sample_decide_payload)}, store=store)
        all_decs = store.all_decisions()
        d_id = all_decs[0]["decision_id"]

        outcome_event = {
            "body": json.dumps({
                "decision_id": d_id,
                "run_id": "test_run_101",
                "adopted": True,
                "kwh_shifted": 2.5,
                "savings_inr": 42.0,
                "opted_out": False,
            })
        }

        resp = outcomes.handler(outcome_event, store=store)
        assert resp["statusCode"] == 202
        body = json.loads(resp["body"])
        assert body["status"] == "accepted"
        assert body["mode"] == "synchronous"

        # Check updated decision
        updated_dec = store.get_decision(d_id)
        assert updated_dec["outcome"]["adopted"] is True
        assert updated_dec["outcome"]["kwh_shifted"] == 2.5

    def test_outcomes_sqs_enqueue(self):
        mock_sqs = MagicMock()
        mock_sqs.send_message.return_value = {"MessageId": "msg_001"}

        outcome_event = {
            "body": json.dumps({
                "decision_id": "d_123",
                "run_id": "run_fifo",
                "adopted": False,
            })
        }

        resp = outcomes.handler(outcome_event, sqs_client=mock_sqs)
        assert resp["statusCode"] == 202
        body = json.loads(resp["body"])
        assert body["mode"] == "enqueued"
        mock_sqs.send_message.assert_called_once()
        kwargs = mock_sqs.send_message.call_args[1]
        assert kwargs["MessageGroupId"] == "run_fifo"
        assert kwargs["MessageDeduplicationId"] == "d_123"

    def test_outcomes_missing_decision_id(self):
        resp = outcomes.handler({"body": json.dumps({"run_id": "r1"})})
        assert resp["statusCode"] == 400


class TestRewardUpdateHandler:
    def test_reward_update_sqs_records(self, sample_decide_payload):
        store = InMemoryStore()
        decide.handler({"body": json.dumps(sample_decide_payload)}, store=store)
        all_decs = store.all_decisions()
        d_id = all_decs[0]["decision_id"]

        sqs_event = {
            "Records": [
                {
                    "messageId": "m1",
                    "body": json.dumps({
                        "decision_id": d_id,
                        "run_id": "test_run_101",
                        "adopted": True,
                        "kwh_shifted": 3.0,
                        "savings_inr": 50.0,
                    }),
                }
            ]
        }

        mock_s3 = MagicMock()
        resp = reward_update.handler(sqs_event, store=store, s3_client=mock_s3)
        assert resp["status"] == "ok"
        assert resp["processed"] == 1
        assert resp["metrics"]["updated_count"] == 1
        mock_s3.put_object.assert_called_once()

    def test_reward_update_empty_records(self):
        store = InMemoryStore()
        resp = reward_update.handler({"Records": []}, store=store)
        assert resp["processed"] == 0


class TestMetricsHandler:
    def test_metrics_missing_run_id(self):
        resp = metrics.handler({"queryStringParameters": {}})
        assert resp["statusCode"] == 400

    def test_metrics_aggregation(self, sample_decide_payload):
        store = InMemoryStore()
        decide.handler({"body": json.dumps(sample_decide_payload)}, store=store)

        resp = metrics.handler(
            {"queryStringParameters": {"run_id": "test_run_101"}},
            store=store,
        )
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["run_id"] == "test_run_101"
        assert body["summary"]["total_decisions"] == 2
        assert "timesteps" in body
        assert len(body["timesteps"]) == 1


class TestDecisionGetHandler:
    def test_decision_get_found(self, sample_decide_payload):
        store = InMemoryStore()
        decide.handler({"body": json.dumps(sample_decide_payload)}, store=store)
        d_id = store.all_decisions()[0]["decision_id"]

        resp = decision_get.handler({"pathParameters": {"id": d_id}}, store=store)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["decision_id"] == d_id

    def test_decision_get_not_found(self):
        store = InMemoryStore()
        resp = decision_get.handler({"pathParameters": {"id": "nonexistent"}}, store=store)
        assert resp["statusCode"] == 404


class TestExplainHandler:
    def test_explain_not_found(self):
        store = InMemoryStore()
        resp = explain.handler({"body": json.dumps({"decision_id": "nonexistent"})}, store=store)
        assert resp["statusCode"] == 404

    def test_explain_found_decision(self, sample_decide_payload):
        store = InMemoryStore()
        decide.handler({"body": json.dumps(sample_decide_payload)}, store=store)
        d_id = store.all_decisions()[0]["decision_id"]

        resp = explain.handler({"body": json.dumps({"decision_id": d_id})}, store=store)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["decision_id"] == d_id
        assert "explanation" in body
        assert "facts" in body


class TestEventsHandler:
    def test_valid_events(self):
        for evt in ["heatwave", "solar_drop", "station_outage", "tariff_change"]:
            resp = events.handler({"body": json.dumps({"event_type": evt, "parameters": {"temp_c": 44.0}})})
            assert resp["statusCode"] == 200
            body = json.loads(resp["body"])
            assert body["status"] == "applied"
            assert body["event_type"] == evt

    def test_invalid_event(self):
        resp = events.handler({"body": json.dumps({"event_type": "alien_invasion"})})
        assert resp["statusCode"] == 400


class TestGridNudgeClient:
    def test_client_full_in_process_workflow(self, sample_decide_payload):
        client = GridNudgeClient()
        assert not client.is_remote

        # 1. Decide
        decisions = client.decide(sample_decide_payload)
        assert len(decisions) == 2
        d_id = decisions[0]["decision_id"]

        # 2. Get Decision
        fetched = client.get_decision(d_id)
        assert fetched is not None
        assert fetched["decision_id"] == d_id

        # 3. Explain
        explanation = client.explain(d_id)
        assert "explanation" in explanation
        assert "facts" in explanation

        # 4. Post Outcome
        res = client.post_outcome({
            "decision_id": d_id,
            "run_id": "test_run_101",
            "adopted": True,
            "kwh_shifted": 4.0,
            "savings_inr": 60.0,
        })
        assert res["status"] == "accepted"

        # 5. Get Metrics
        met = client.get_metrics("test_run_101")
        assert met["summary"]["total_decisions"] == 2
        assert met["summary"]["kwh_shifted_total"] >= 4.0

        # 6. Inject Event
        evt_res = client.inject_event("heatwave", {"temp_c": 42.0})
        assert evt_res["status"] == "applied"


class TestDynamoStoreMocked:
    def test_mocked_dynamo_store_operations(self):
        mock_resource = MagicMock()
        mock_table = MagicMock()
        mock_resource.Table.return_value = mock_table

        # Setup mock returns
        mock_table.get_item.side_effect = [
            {"Item": {"user_id": "u1", "fatigue": 0.1}},  # get_users
            {"Item": {"model_id": "lints", "version": 2}},  # get_model
            {"Item": {"decision_id": "d1", "run_id": "r1"}},  # get_decision
        ]
        mock_table.query.return_value = {
            "Items": [{"decision_id": "d1", "run_id": "r1", "sim_time": "2026-10-10T18:00"}]
        }

        store = DynamoStore(dynamodb_resource=mock_resource)

        # Users
        users = store.get_users(["u1"])
        assert "u1" in users

        # Model
        model = store.get_model("lints")
        assert model["version"] == 2

        # Decisions
        store.put_decisions([{"decision_id": "d1", "run_id": "r1"}])
        dec = store.get_decision("d1")
        assert dec["decision_id"] == "d1"

        # Query by run
        by_run = store.query_decisions_by_run("r1")
        assert len(by_run) == 1

    def test_get_default_store_selection(self, monkeypatch):
        monkeypatch.delenv("AWS_LAMBDA_FUNCTION_NAME", raising=False)
        monkeypatch.delenv("USE_DYNAMO_STORE", raising=False)
        assert isinstance(get_default_store(), InMemoryStore)

        monkeypatch.setenv("USE_DYNAMO_STORE", "1")
        assert isinstance(get_default_store(), DynamoStore)
