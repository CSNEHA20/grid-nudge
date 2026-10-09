"""Safety module for GridNudge: Python invariants, Cedar policy evaluation, and fail-silent architecture."""

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
    DEFAULT_LIMITS,
    SafetyLimits,
    filter_safe_plans,
    load_safety_limits,
    validate_plan_invariants,
)

__all__ = [
    "SafetyLimits",
    "DEFAULT_LIMITS",
    "load_safety_limits",
    "validate_plan_invariants",
    "filter_safe_plans",
    "evaluate_cedar_policy",
    "check_nudge_authorization",
    "is_quiet_hours",
    "build_fail_silent_record",
    "fail_silent_guard",
]
