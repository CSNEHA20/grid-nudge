"""Tests for GridNudge data contracts, JSON schemas, fixtures, and TypeScript alignments."""

import json
from pathlib import Path
import jsonschema
import pytest
from pydantic import ValidationError

from gridnudge.contracts import (
    Allocation,
    DecisionRecord,
    Language,
    Outcome,
    Persuasion,
    Safety,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = ROOT_DIR / "contracts"
FIXTURES_DIR = ROOT_DIR / "fixtures"


@pytest.fixture
def decision_schema():
    schema_path = CONTRACTS_DIR / "decision_record.schema.json"
    assert schema_path.exists(), "decision_record.schema.json must exist"
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_decisions_json():
    fixtures_path = FIXTURES_DIR / "decisions.sample.json"
    assert fixtures_path.exists(), "decisions.sample.json fixture must exist"
    with open(fixtures_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_contracts_schema_exists_and_is_valid(decision_schema):
    """Ensure the JSON schema itself is valid Draft 2020-12 schema."""
    jsonschema.Draft202012Validator.check_schema(decision_schema)


def test_typescript_contract_file_exists():
    """Verify TypeScript types file exists and defines core interfaces."""
    ts_path = CONTRACTS_DIR / "ts" / "decision-record.d.ts"
    assert ts_path.exists()
    content = ts_path.read_text(encoding="utf-8")
    assert "export interface DecisionRecord" in content
    assert "export interface Journey" in content
    assert "export interface Safety" in content
    assert "export interface Persuasion" in content
    assert "export type PlanType" in content
    assert "export type Frame" in content


def test_fixtures_validate_against_json_schema(decision_schema, sample_decisions_json):
    """Every record in sample fixtures must validate against the exported JSON schema."""
    validator = jsonschema.Draft202012Validator(decision_schema)
    assert len(sample_decisions_json) >= 3, "Sample must have at least 3 records"
    for record in sample_decisions_json:
        validator.validate(record)


def test_fixtures_deserialize_to_pydantic_models(sample_decisions_json):
    """Every record in sample fixtures must cleanly deserialize to DecisionRecord."""
    models = [DecisionRecord.model_validate(rec) for rec in sample_decisions_json]
    assert len(models) == 3

    # Check normal nudge
    nudge = models[0]
    assert nudge.decision_id == "d_001_nudge_cost"
    assert nudge.safety.invariants_ok is True
    assert nudge.safety.cedar == "ALLOW"
    assert nudge.persuasion.frame == "cost"
    assert nudge.allocation.selected is True
    assert nudge.language.verified is True
    assert nudge.language.message is not None

    # Check safety veto
    veto = models[1]
    assert veto.decision_id == "d_002_safety_veto"
    assert veto.safety.invariants_ok is False
    assert veto.safety.cedar == "DENY"
    assert len(veto.safety.vetoed) > 0
    assert "0.82 < threshold 0.90" in veto.safety.vetoed[0]
    assert veto.allocation.selected is False
    assert veto.persuasion.frame == "none"
    assert veto.language.message is None

    # Check learned silence
    silence = models[2]
    assert silence.decision_id == "d_003_learned_silence"
    assert silence.safety.invariants_ok is True
    assert silence.safety.cedar == "ALLOW"
    assert silence.persuasion.frame == "none"
    assert silence.allocation.selected is False
    assert silence.persuasion.uplift_mean <= 0.0
    assert silence.language.message is None


def test_decision_record_roundtrip():
    """Verify serialization to JSON and deserialization back preserves identity."""
    record = DecisionRecord(
        decision_id="d_test_roundtrip",
        run_id="run_test",
        sim_time="2026-10-10T12:00:00Z",
        user_id="user_roundtrip",
        ev={"model": "Test EV", "battery_kwh": 50.0},
        safety=Safety(invariants_ok=True, cedar="ALLOW", vetoed=[]),
        persuasion=Persuasion(
            frame="none",
            uplift_mean=0.0,
            uplift_p10=0.0,
            propensity=1.0,
            explored=False,
        ),
        allocation=Allocation(selected=False, shadow_price=0.0),
        language=Language(),
        outcome=Outcome(),
    )
    dumped = record.model_dump(mode="json")
    reloaded = DecisionRecord.model_validate(dumped)
    assert reloaded == record


def test_strict_contract_rejects_extra_fields():
    """Ensure extra unexpected fields trigger ValidationError per contract freeze."""
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="d_test_invalid",
            run_id="run_test",
            sim_time="2026-10-10T12:00:00Z",
            user_id="user_test",
            ev={},
            safety=Safety(invariants_ok=True, cedar="ALLOW"),
            persuasion=Persuasion(
                frame="none",
                uplift_mean=0.0,
                uplift_p10=0.0,
                propensity=1.0,
                explored=False,
            ),
            allocation=Allocation(selected=False, shadow_price=0.0),
            unknown_arbitrary_field="illegal_value",
        )


def test_other_fixtures_exist_and_are_valid_json():
    """Verify timeline, evaluation, calibration, and flexibility fixtures exist and are valid JSON."""
    expected_files = [
        "metrics.timeline.json",
        "evaluation.summary.json",
        "calibration.json",
        "flexibility.json",
    ]
    for filename in expected_files:
        path = FIXTURES_DIR / filename
        assert path.exists(), f"Fixture {filename} must exist"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert isinstance(data, dict)
            assert "provenance" in data or "policies" in data or "timesteps" in data
