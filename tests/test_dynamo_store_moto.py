"""Moto-based integration tests for DynamoStore, verifying float/Decimal serialization and concurrency."""
import boto3
import numpy as np
import pytest
from moto import mock_aws

from gridnudge.persuasion.lints import LinTS
from gridnudge.state import ConcurrencyError, DynamoStore


@pytest.fixture
def store(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "x")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        db = boto3.resource("dynamodb")
        db.create_table(
            TableName="u",
            KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "user_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        db.create_table(
            TableName="m",
            KeySchema=[{"AttributeName": "model_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "model_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        db.create_table(
            TableName="d",
            KeySchema=[{"AttributeName": "decision_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "decision_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield DynamoStore(user_table="u", model_table="m", decision_table="d", dynamodb_resource=db)


def test_users_roundtrip_floats(store):
    store.put_users({"1": {"fatigue": 0.4, "nudges_today": 1}})
    got = store.get_users(["1"])["1"]
    assert abs(got["fatigue"] - 0.4) < 1e-9 and got["nudges_today"] == 1


def test_model_roundtrip_exact(store):
    st = LinTS(seed=1).get_state()
    store.put_model("lints", st, 0)
    back = store.get_model("lints")
    assert np.allclose(np.array(back["A"]), np.array(st["A"]))


def test_model_version_conflict(store):
    st = LinTS(seed=1).get_state()
    store.put_model("lints", st, 0)
    with pytest.raises(ConcurrencyError):
        store.put_model("lints", st, 0)  # already exists, expected_version=0 must fail


def test_decision_roundtrip(store):
    store.put_decisions([{"decision_id": "d1", "run_id": "r", "score": 0.5}])
    assert store.get_decision("d1")["score"] == 0.5


def test_journey_calibration_sklearn_blocked(monkeypatch):
    import sys
    # Verify calibration works without sklearn in runtime environment
    monkeypatch.setitem(sys.modules, "sklearn", None)
    monkeypatch.setitem(sys.modules, "sklearn.isotonic", None)
    from gridnudge.perception.journey import JourneyCalibrator
    calibrator = JourneyCalibrator()
    calibrated = calibrator.calibrate(0.85)
    assert 0.0 <= calibrated <= 1.0

