"""Test to prevent demo literals and unverified fabricated numbers in dashboard.

Enforces Rule 1.1 ("Never invent numbers") and C2 resolution:
Ensures all dashboard components avoid hand-authored demo literals (e.g. 14.2, 118)
and that replay and evaluation fixtures have genuine provenance.
"""

from pathlib import Path
import json
import re
import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_SRC_DIR = ROOT_DIR / "dashboard" / "src"
FIXTURES_DIR = ROOT_DIR / "fixtures"
RESULTS_DIR = ROOT_DIR / "results"
PUBLIC_REPLAY_FILE = ROOT_DIR / "dashboard" / "public" / "replay" / "timeline.json"


def test_no_banned_demo_literals_in_dashboard_source():
    """Ensure dashboard source files do not contain ungrounded demo literals."""
    if not DASHBOARD_SRC_DIR.exists():
        pytest.skip("Dashboard src directory not found")

    banned_patterns = [
        (re.compile(r"\b14\.2\b"), "14.2 (unverified peak MW / reduction literal)"),
        (re.compile(r"broadcastPct\s*=\s*118"), "broadcastPct = 118 (hardcoded 118% stress)"),
        (re.compile(r"broadcastNudges\s*=\s*4\.0"), "broadcastNudges = 4.0 (hardcoded 4.0 nudges)"),
        (re.compile(r"usedPct\s*=\s*62\b"), "usedPct = 62 (hardcoded 62% attention budget)"),
    ]

    violations = []
    for code_file in DASHBOARD_SRC_DIR.rglob("*.[tj]sx"):
        content = code_file.read_text(encoding="utf-8")
        for pattern, desc in banned_patterns:
            matches = list(pattern.finditer(content))
            if matches:
                violations.append(f"{code_file.relative_to(ROOT_DIR)}: found {desc} ({len(matches)} matches)")

    assert not violations, f"Banned demo literals detected:\n" + "\n".join(violations)


def test_replay_and_eval_fixtures_provenance():
    """Verify that generated replay and evaluation fixtures contain provenance 'Simulation'."""
    eval_file = FIXTURES_DIR / "evaluation.summary.json"
    assert eval_file.exists(), "evaluation.summary.json must exist"
    with open(eval_file, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    assert eval_data.get("provenance") == "Simulation"
    assert len(eval_data.get("policies", [])) >= 4

    calib_file = FIXTURES_DIR / "calibration.json"
    assert calib_file.exists(), "calibration.json must exist"
    with open(calib_file, "r", encoding="utf-8") as f:
        calib_data = json.load(f)
    assert calib_data.get("provenance") == "Simulation"

    replay_file = RESULTS_DIR / "replay" / "timeline.json"
    if replay_file.exists():
        with open(replay_file, "r", encoding="utf-8") as f:
            replay_data = json.load(f)
        assert replay_data.get("provenance") == "Simulation"

    assert PUBLIC_REPLAY_FILE.exists(), "dashboard/public/replay/timeline.json must exist"
    with open(PUBLIC_REPLAY_FILE, "r", encoding="utf-8") as f:
        pub_replay_data = json.load(f)
    assert pub_replay_data.get("provenance") == "Simulation"
