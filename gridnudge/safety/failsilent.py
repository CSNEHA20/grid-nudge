"""Fail-silent architecture implementation for GridNudge.

NON-NEGOTIABLE AGENT RULE (AGENTS.md Section 1.3):
If any critical component (perception, planner, Cedar, bandit, allocator, or verifier)
throws, times out, produces malformed/impossible values, or fails verification:
    - Send NO nudge
    - Log the exact failure
    - Return a safe, auditable DecisionRecord with fail_silent=True and frame="none".
    - Never degrade into an unsafe recommendation.

Per GEMINI.md Section 18:
Auditing explicitly distinguishes between a valid learned "none" action and a fail-silent fallback.
"""

from datetime import datetime
import functools
import logging
from typing import Any, Callable, Dict, Optional, TypeVar
import uuid

from gridnudge.contracts import (
    Allocation,
    DecisionRecord,
    Language,
    Outcome,
    Persuasion,
    Safety,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


def build_fail_silent_record(
    decision_id: Optional[str] = None,
    run_id: str = "run_default",
    sim_time: Optional[str] = None,
    user_id: str = "unknown_user",
    ev: Optional[Dict[str, Any]] = None,
    error_message: str = "Unknown critical failure",
    vetoed_reasons: Optional[list] = None,
) -> DecisionRecord:
    """Build a typed DecisionRecord representing a safe fail-silent fallback."""
    d_id = decision_id or f"d_failsafe_{uuid.uuid4().hex[:8]}"
    t_iso = sim_time or datetime.now().isoformat()
    ev_dict = ev or {"battery_kwh": 40.0, "current_soc": 0.5}

    logger.warning("Fail-silent activated for decision %s (user %s): %s", d_id, user_id, error_message)

    return DecisionRecord(
        decision_id=d_id,
        run_id=run_id,
        sim_time=t_iso,
        user_id=str(user_id),
        ev=ev_dict,
        journey=None,
        battery=None,
        station=None,
        grid=None,
        plans=[],
        safety=Safety(
            invariants_ok=False,
            cedar="ERROR",
            vetoed=vetoed_reasons or [f"Fail-silent: {error_message}"],
        ),
        persuasion=Persuasion(
            chosen_plan=None,
            frame="none",
            timing=None,
            uplift_mean=0.0,
            uplift_p10=0.0,
            propensity=1.0,
            explored=False,
        ),
        allocation=Allocation(
            selected=False,
            shadow_price=0.0,
            slot=None,
        ),
        language=Language(
            message=None,
            facts_used={},
            verified=False,
            source="none",
        ),
        outcome=Outcome(),
        fail_silent=True,
        error=error_message,
    )


def fail_silent_guard(
    fallback_factory: Optional[Callable[[Exception], Any]] = None,
) -> Callable:
    """Decorator to catch unexpected errors in decision path and trigger fail-silent handling."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                logger.error("Exception in %s: %s", func.__name__, exc, exc_info=True)
                if fallback_factory is not None:
                    return fallback_factory(exc)
                # If function returns DecisionRecord or is a top-level decider
                user_id = kwargs.get("user_id", "unknown")
                return build_fail_silent_record(
                    user_id=str(user_id),
                    error_message=f"{func.__name__} crashed: {str(exc)}",
                )

        return wrapper

    return decorator
