"""Tests for M8b (Language Layer & Numeric Verifier) and M8c (Operator Copilot Tools).

Validates strict numeric traceability, forbidden claim rejection, Bedrock/template
rendering fallback, decision auditing, and scenario injection validation.
"""

from agent.tools import (
    compare_policies,
    explain_veto,
    get_decision,
    inject_scenario,
)
from gridnudge.contracts import Language
from gridnudge.language.render import render_nudge_message
from gridnudge.language.verify import (
    extract_allowed_numbers,
    verify_nudge_text,
)


class TestNumericVerifier:
    """Tests for M8b numeric verification and hallucination detection."""

    def test_verifier_accepts_traceable_numbers(self):
        """Verifier passes when all numbers correspond to approved facts."""
        facts = {
            "saving_inr": 51.3,
            "start_time": "22:30",
            "journey_conf": 0.94,
        }
        allowed = extract_allowed_numbers(facts)
        assert "51.3" in allowed or "51" in allowed
        assert "22" in allowed and "30" in allowed
        assert "94" in allowed

        valid_msg = "Charge at 22:30 to save \u20b951 with 94% journey confidence."
        is_valid, reasons = verify_nudge_text(valid_msg, facts)
        assert is_valid
        assert len(reasons) == 0

    def test_verifier_rejects_hallucinated_numbers(self):
        """Verifier strictly rejects messages with fabricated numerical claims."""
        facts = {
            "saving_inr": 51.3,
            "start_time": "22:30",
        }
        # Text invents ₹75 and 150 km!
        hallucinated_msg = "Shift your charging to save \u20b975 and gain 150 km range."
        is_valid, reasons = verify_nudge_text(hallucinated_msg, facts)
        assert not is_valid
        assert any("Unsupported numbers detected" in r for r in reasons)

    def test_verifier_rejects_forbidden_claims(self):
        """Rejects forbidden claims such as 'guarantee', 'will last', or '100%'."""
        facts = {"saving_inr": 50.0}
        bad_msg = "We guarantee 100% battery protection with this schedule."
        is_valid, reasons = verify_nudge_text(bad_msg, facts)
        assert not is_valid
        assert any("Forbidden claim detected" in r for r in reasons)


class TestMessageRendering:
    """Tests for message rendering and fallback behavior."""

    def test_render_message_template_fallback(self):
        """Renders verified template when use_llm is False."""
        facts = {
            "saving_inr": 45,
            "start_time": "23:00",
        }
        lang_res = render_nudge_message(facts, frame="cost", use_llm=False)
        assert isinstance(lang_res, Language)
        assert lang_res.source == "template"
        assert lang_res.verified is True
        assert "45" in lang_res.message
        assert "23:00" in lang_res.message

    def test_render_none_frame_emits_silence(self):
        """Rendering 'none' frame produces empty verified message."""
        lang_res = render_nudge_message({}, frame="none")
        assert lang_res.message is None
        assert lang_res.source == "none"
        assert lang_res.verified is True


class TestCopilotTools:
    """Tests for M8c Operator Copilot tools."""

    def test_get_decision_from_fixtures(self):
        """Copilot retrieves sample decision record by ID."""
        decision = get_decision("d_002_safety_veto")
        assert decision.get("decision_id") == "d_002_safety_veto"
        assert "ev" in decision
        assert "safety" in decision

    def test_explain_veto_cites_factual_reasons(self):
        """Copilot provides human-readable explanation citing decision ID and veto reasons."""
        explanation = explain_veto("d_002_safety_veto")
        assert explanation["decision_id"] == "d_002_safety_veto"
        assert explanation["was_vetoed"] is True
        assert explanation["cedar_verdict"] == "DENY"
        assert len(explanation["vetoed_reasons"]) > 0
        assert "d_002_safety_veto" in explanation["explanation"]

    def test_compare_policies_computes_peak_reduction(self):
        """Copilot computes policy deltas between baseline and GridNudge."""
        metrics_b0 = {"peak_load_mw": 19.7, "shifted_kwh": 0.0, "nudges_per_user": 0}
        metrics_b4 = {"peak_load_mw": 15.2, "shifted_kwh": 4500.0, "nudges_per_user": 2}

        comparison = compare_policies(metrics_b0, metrics_b4)
        assert comparison["peak_reduction_pct"] > 20.0
        assert comparison["additional_shifted_kwh"] == 4500.0
        assert "reduces peak load by" in comparison["summary"]

    def test_inject_scenario_validation(self):
        """Validates environmental scenario injection and rejects invalid types."""
        valid = inject_scenario("heatwave", {"temp_rise_c": 10.0})
        assert valid["status"] == "validated"
        assert valid["scenario_config"]["temp_rise_c"] == 10.0

        invalid = inject_scenario("unknown_blizzard")
        assert invalid["status"] == "error"
