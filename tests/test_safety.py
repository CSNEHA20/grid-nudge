"""Tests for M5 Safety module: Python invariants, Cedar policy evaluation, and fail-silent architecture.

Validates Safety Filter #1, hard journey threshold gating, quiet hours, opt-outs,
daily frequency limits, and graceful degradation to silence.
"""

from gridnudge.contracts import Plan
from gridnudge.safety.cedar_check import (
    check_nudge_authorization,
    evaluate_cedar_policy,
    is_quiet_hours,
)
from gridnudge.safety.failsilent import (
    build_fail_silent_record,
    fail_silent_guard,
)
from gridnudge.safety.invariants import (
    filter_safe_plans,
    validate_plan_invariants,
)


class TestPythonInvariants:
    """Tests for Python physical and operational safety invariants."""

    def test_safety_veto_low_journey_confidence(self):
        """Plans with journey_conf_lb < 0.90 must be strictly vetoed with clear reason."""
        risky_plan = Plan(
            plan_id="plan_delay_risky",
            type="delay",
            start="2026-10-11T02:00:00+05:30",
            kw=7.4,
            where="home",
            outcomes={
                "cost_inr": 154.0,
                "journey_conf_lb": 0.82,  # Below 0.90 threshold!
                "arrival_soc_q10": 0.06,
                "grid_value": 1.2,
                "battery_stress_delta": -0.04,
                "wait_min": 0.0,
            },
        )
        ev_context = {"max_ac_kw": 7.4, "charger_kw": 7.4}

        is_safe, reasons = validate_plan_invariants(risky_plan, ev_context)
        assert not is_safe
        assert any("journey_conf_lb 0.82 < threshold 0.90" in r for r in reasons)

    def test_filter_safe_plans_drops_unsafe_and_keeps_safe(self):
        """filter_safe_plans removes unsafe candidate plans so bandit never sees them."""
        safe_plan = Plan(
            plan_id="plan_default_safe",
            type="default",
            start="2026-10-10T19:00:00+05:30",
            kw=7.4,
            where="home",
            outcomes={
                "cost_inr": 230.0,
                "journey_conf_lb": 0.95,
                "arrival_soc_q10": 0.15,
                "grid_value": -0.5,
                "battery_stress_delta": 0.0,
                "wait_min": 0.0,
            },
        )
        risky_plan = Plan(
            plan_id="plan_delay_risky",
            type="delay",
            start="2026-10-11T02:00:00+05:30",
            kw=7.4,
            where="home",
            outcomes={
                "cost_inr": 154.0,
                "journey_conf_lb": 0.84,
                "arrival_soc_q10": 0.08,
                "grid_value": 1.2,
                "battery_stress_delta": -0.04,
                "wait_min": 0.0,
            },
        )
        ev_context = {"max_ac_kw": 7.4}

        safe_plans, vetoed = filter_safe_plans([safe_plan, risky_plan], ev_context)
        assert len(safe_plans) == 1
        assert safe_plans[0].plan_id == "plan_default_safe"
        assert len(vetoed) > 0

    def test_reject_power_exceeding_vehicle_limits(self):
        """Plans requesting charging power beyond vehicle limits must be rejected."""
        overpowered_plan = Plan(
            plan_id="plan_fast_overload",
            type="default",
            start="2026-10-10T19:00:00+05:30",
            kw=22.0,  # 22 kW requested on 7.4 kW vehicle charger
            where="home",
            outcomes={"journey_conf_lb": 0.96, "wait_min": 0.0},
        )
        ev_context = {"max_ac_kw": 7.4}

        is_safe, reasons = validate_plan_invariants(overpowered_plan, ev_context)
        assert not is_safe
        assert any("exceeds vehicle limit" in r for r in reasons)

    def test_reject_rebound_feeder_peak(self):
        """Plans creating an overload peak above feeder capacity must be rejected."""
        peak_plan = Plan(
            plan_id="plan_rebound_peak",
            type="delay",
            start="2026-10-10T22:30:00+05:30",
            kw=7.4,
            where="home",
            outcomes={
                "journey_conf_lb": 0.95,
                "creates_new_peak": True,  # Overload flagged!
                "wait_min": 0.0,
            },
        )
        is_safe, reasons = validate_plan_invariants(peak_plan, {"max_ac_kw": 7.4})
        assert not is_safe
        assert any("exceed feeder capacity" in r for r in reasons)

    def test_reject_non_finite_numerical_outcomes(self):
        """Reject plans with NaN journey confidence or negative queue wait."""
        nan_plan = Plan(
            plan_id="plan_nan",
            type="default",
            start="2026-10-10T19:00:00+05:30",
            kw=7.4,
            where="home",
            outcomes={"journey_conf_lb": float("nan"), "wait_min": -5.0},
        )
        is_safe, reasons = validate_plan_invariants(nan_plan, {"max_ac_kw": 7.4})
        assert not is_safe
        assert len(reasons) >= 2


class TestCedarPolicy:
    """Tests for Cedar policy authorization and rule compliance."""

    def test_cedar_permits_when_all_conditions_satisfied(self):
        """Cedar permits SendNudge when physical, operational, and user checks all pass."""
        context = {
            "optedOut": False,
            "quietHours": False,
            "nudgesToday": 1,
            "journeyConfLbBps": 9400,  # 0.94 >= 0.90
            "invariantsOk": True,
            "vehicleSupportsPlan": True,
        }
        verdict = evaluate_cedar_policy("user_101", "d_001", context)
        assert verdict == "ALLOW"

    def test_cedar_forbid_on_unsafe_journey_confidence(self):
        """Cedar belt-and-braces FORBID rule triggers whenever journey confidence < 9000 bps."""
        context = {
            "optedOut": False,
            "quietHours": False,
            "nudgesToday": 0,
            "journeyConfLbBps": 8800,  # 0.88 < 0.90
            "invariantsOk": True,
            "vehicleSupportsPlan": True,
        }
        verdict = evaluate_cedar_policy("user_101", "d_001", context)
        assert verdict == "DENY"

    def test_cedar_denies_on_opt_out_or_daily_cap(self):
        """Cedar denies nudging when user opted out or reached 3 nudges today."""
        # Opt-out
        context_opt = {
            "optedOut": True,
            "quietHours": False,
            "nudgesToday": 0,
            "journeyConfLbBps": 9500,
            "invariantsOk": True,
            "vehicleSupportsPlan": True,
        }
        assert evaluate_cedar_policy("user_101", "d_001", context_opt) == "DENY"

        # Daily cap (3 nudges)
        context_cap = {
            "optedOut": False,
            "quietHours": False,
            "nudgesToday": 3,
            "journeyConfLbBps": 9500,
            "invariantsOk": True,
            "vehicleSupportsPlan": True,
        }
        assert evaluate_cedar_policy("user_101", "d_001", context_cap) == "DENY"

    def test_quiet_hours_detection(self):
        """Nighttime hours (23:00 to 06:00) trigger quiet hours."""
        assert is_quiet_hours(23.5) is True
        assert is_quiet_hours(2.0) is True
        assert is_quiet_hours(5.9) is True
        assert is_quiet_hours(14.0) is False
        assert is_quiet_hours(19.0) is False

    def test_check_nudge_authorization_helper(self):
        """Helper function checks plan and returns structured reasons."""
        safe_plan = Plan(
            plan_id="plan_p1",
            type="delay",
            start="2026-10-10T22:30:00+05:30",
            kw=7.4,
            where="home",
            outcomes={"journey_conf_lb": 0.92, "wait_min": 0.0},
        )
        verdict, reasons = check_nudge_authorization(
            user_id="user_101",
            decision_id="d_001",
            plan=safe_plan,
            ev_context={"max_ac_kw": 7.4},
            hour_of_day=19.0,  # 7 PM (outside quiet hours)
            nudges_today=1,
            opted_out=False,
            invariants_ok=True,
        )
        assert verdict == "ALLOW"
        assert len(reasons) == 0


class TestFailSilent:
    """Tests for fail-silent architecture and safe error degradation."""

    def test_failsilent_record_structure(self):
        """Fail-silent record must send no nudge, mark fail_silent=True, and log error."""
        record = build_fail_silent_record(
            decision_id="d_test_err",
            user_id="user_999",
            error_message="Cedar evaluation connection timeout",
        )
        assert record.fail_silent is True
        assert record.error == "Cedar evaluation connection timeout"
        assert record.persuasion.frame == "none"
        assert record.persuasion.chosen_plan is None
        assert record.allocation.selected is False
        assert record.language.message is None
        assert record.language.source == "none"
        assert record.safety.cedar == "ERROR"

    def test_failsilent_guard_catches_unhandled_exception(self):
        """fail_silent_guard decorator intercepts unexpected crashes and emits fail-silent record."""
        @fail_silent_guard()
        def buggy_pipeline_component(user_id: str):
            raise RuntimeError("Corrupted sensor data or database failure")

        res = buggy_pipeline_component(user_id="user_404")
        assert res.fail_silent is True
        assert "buggy_pipeline_component crashed" in res.error
        assert res.persuasion.frame == "none"
