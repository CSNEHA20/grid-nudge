"""Baseline charging and nudging policies for benchmarking GridNudge.

B0: Uncontrolled default charging (charge immediately upon plugging in).
B1: Simple rule-based shifting (nudge every plugged EV during peak to delay).
B2: Safe rule-based planner (nudge only when SOC >= 25% to preserve reserve).
"""

from typing import Any, Dict, List
from twin.runner import run_simulation
from twin.world import World


def policy_b0(world: World) -> List[Dict[str, Any]]:
    """B0: Uncontrolled baseline. Zero interventions."""
    return []


def create_policy_b1(max_rate: float = 1.0) -> Any:
    """Create B1 policy with optional rate capping for Pareto evaluation."""
    def policy_fn(world: World) -> List[Dict[str, Any]]:
        state = world.grid_state()
        if not state.get("is_peak_window", False):
            return []

        candidates = world.candidates()
        decisions = []
        for c in candidates:
            if max_rate < 1.0 and (int(c["user_id"]) % 100) >= int(max_rate * 100):
                continue
            decisions.append({
                "decision_id": f"b1_s{world.current_step}_u{c['user_id']}",
                "user_id": c["user_id"],
                "plan": {"type": "delay"},
                "frame": "cost",
                "timing": "at_plug_in",
                "savings_inr": 65.0,
                "delay_hours": 3.5,
            })
        return decisions
    return policy_fn


def policy_b1(world: World) -> List[Dict[str, Any]]:
    """B1: Simple rule-based peak shifting."""
    return create_policy_b1(max_rate=1.0)(world)


def create_policy_b2(max_rate: float = 1.0) -> Any:
    """Create B2 policy with optional rate capping for Pareto evaluation."""
    def policy_fn(world: World) -> List[Dict[str, Any]]:
        state = world.grid_state()
        if not state.get("is_peak_window", False):
            return []

        candidates = world.candidates()
        decisions = []
        for c in candidates:
            dep_step = c.get("departure_step", -1)
            too_soon = (dep_step is not None and dep_step > world.current_step and (dep_step - world.current_step) * (world.step_minutes / 60.0) < 5.0)

            if c.get("nudges_today", 0) >= 1 or c.get("soc", 0.0) < 0.25 or too_soon:
                continue

            if max_rate < 1.0 and (int(c["user_id"]) % 100) >= int(max_rate * 100):
                continue

            decisions.append({
                "decision_id": f"b2_s{world.current_step}_u{c['user_id']}",
                "user_id": c["user_id"],
                "plan": {"type": "delay"},
                "frame": "cost",
                "timing": "at_plug_in",
                "savings_inr": 65.0,
                "delay_hours": 3.5,
            })
        return decisions
    return policy_fn


def policy_b2(world: World) -> List[Dict[str, Any]]:
    """B2: Safe rule-based planner."""
    return create_policy_b2(max_rate=1.0)(world)


def create_policy_b3(
    seed: int = 42,
    run_id: str = "b3_bandit_no_alloc",
    sample_rate: float = 1.0,
) -> Any:
    """B3: Bandit without fleet allocator (no attention budget cap, no anti-herding staggering)."""
    from gridnudge.pipeline import create_pipeline_policy
    from gridnudge.persuasion.lints import LinTS
    from gridnudge.state import InMemoryStore

    store = InMemoryStore()
    bandit = LinTS(seed=seed)
    base_fn = create_pipeline_policy(store=store, bandit=bandit, run_id=run_id, apply_allocation=False)

    if sample_rate >= 1.0:
        return base_fn

    def sampled_policy_fn(world: World) -> List[Dict[str, Any]]:
        decisions = base_fn(world)
        if sample_rate >= 1.0:
            return decisions
        filtered = []
        for d in decisions:
            if (int(d.get("user_id", 0)) % 100) < int(sample_rate * 100):
                filtered.append(d)
            else:
                filtered.append({
                    "decision_id": d.get("decision_id"),
                    "user_id": d.get("user_id"),
                    "plan": {"type": "default"},
                    "frame": "none",
                    "timing": None,
                    "savings_inr": 0.0,
                    "delay_hours": 0.0,
                })
        return filtered

    return sampled_policy_fn


_WARM_BANDIT_STATE: Optional[Dict[str, Any]] = None


def get_warm_bandit(seed: int = 42) -> Any:
    """Return a LinTS bandit warm-started on grounded datasets and development seeds >= 100."""
    global _WARM_BANDIT_STATE
    from gridnudge.persuasion.lints import LinTS
    from gridnudge.persuasion.pretrain import get_dataset_trained_bandit

    if _WARM_BANDIT_STATE is None:
        b = get_dataset_trained_bandit(seed=seed)
        _WARM_BANDIT_STATE = b.get_state()

    bandit = LinTS(seed=seed)
    bandit.load_state(_WARM_BANDIT_STATE)
    return bandit


def create_policy_b4(
    seed: int = 42,
    run_id: str = "b4_gridnudge",
    warm_start: bool = True,
    budget_pct: float = 0.08,
) -> Any:
    """B4: Full GridNudge decision policy with StateStore, fleet allocator, and closed-loop learning."""
    from gridnudge.pipeline import create_pipeline_policy
    from gridnudge.persuasion.lints import LinTS
    from gridnudge.state import InMemoryStore

    store = InMemoryStore()
    if warm_start:
        bandit = get_warm_bandit(seed=seed)
    else:
        bandit = LinTS(seed=seed)
    return create_pipeline_policy(
        store=store,
        bandit=bandit,
        run_id=run_id,
        apply_allocation=True,
        budget_pct=budget_pct,
    )


def create_policy_b4a(
    seed: int = 42,
    run_id: str = "b4a_delay_only",
    warm_start: bool = True,
    budget_pct: float = 0.08,
) -> Any:
    """B4a: Ablation policy restricted to delay plans only."""
    from gridnudge.pipeline import create_pipeline_policy
    from gridnudge.persuasion.lints import LinTS
    from gridnudge.state import InMemoryStore

    store = InMemoryStore()
    if warm_start:
        bandit = get_warm_bandit(seed=seed)
    else:
        bandit = LinTS(seed=seed)
    return create_pipeline_policy(
        store=store,
        bandit=bandit,
        run_id=run_id,
        apply_allocation=True,
        allowed_plan_types=["delay"],
        budget_pct=budget_pct,
    )


def create_policy_b4b(
    seed: int = 42,
    run_id: str = "b4b_no_fatigue",
    budget_pct: float = 0.08,
) -> Any:
    """B4b: Ablation policy without fatigue features."""
    from gridnudge.pipeline import create_pipeline_policy
    from gridnudge.persuasion.lints import LinTS
    from gridnudge.state import InMemoryStore

    store = InMemoryStore()
    bandit = LinTS(seed=seed)
    return create_pipeline_policy(
        store=store,
        bandit=bandit,
        run_id=run_id,
        apply_allocation=True,
        disable_fatigue_features=True,
        budget_pct=budget_pct,
    )


def create_policy_oracle(
    seed: int = 42,
) -> Any:
    """Oracle: Twin-informed theoretical upper bound policy.

    Knows the hidden archetype response model and selects the optimal persuasion frame
    and delay plan for safe candidates to maximize peak shaving without inducing opt-outs.
    """
    def oracle_policy_fn(world: World) -> List[Dict[str, Any]]:
        state = world.grid_state()
        if not state.get("is_peak_window", False):
            return []

        candidates = world.candidates()
        decisions: List[Dict[str, Any]] = []

        optimal_frames = {
            "commuter_frugal": "cost",
            "commuter_green": "green",
            "cab_driver": "reassurance",
            "erratic_flex": "convenience",
        }

        max_nudges_per_step = max(1, int(len(candidates) * 0.40))
        nudge_count = 0

        for c in candidates:
            dep_step = c.get("departure_step", -1)
            too_soon = (
                dep_step is not None
                and dep_step > world.current_step
                and (dep_step - world.current_step) * (world.step_minutes / 60.0) < 5.0
            )

            if c.get("nudges_today", 0) >= 1 or c.get("soc", 0.0) < 0.25 or too_soon or c.get("opted_out", False):
                continue

            if nudge_count >= max_nudges_per_step:
                break

            archetype = c.get("archetype", "commuter_frugal")
            best_frame = optimal_frames.get(archetype, "cost")

            decisions.append({
                "decision_id": f"oracle_s{world.current_step}_u{c['user_id']}",
                "user_id": c["user_id"],
                "plan": {"type": "delay"},
                "frame": best_frame,
                "timing": "at_plug_in",
                "savings_inr": 65.0,
                "delay_hours": 3.5,
            })
            nudge_count += 1

        return decisions

    return oracle_policy_fn


def get_policy_by_name(name: str, seed: int = 42) -> Any:
    """Resolve policy runner callable by policy name (B0, B1, B2, B3, B4, B4a, B4b, Oracle)."""
    clean_name = name.upper().strip()
    if clean_name in ("B0", "B0_UNCONTROLLED"):
        return policy_b0
    elif clean_name in ("B1", "B1_RULE_BASED", "B1_BROADCAST"):
        return policy_b1
    elif clean_name in ("B2", "B2_SAFE_PLANNER"):
        return policy_b2
    elif clean_name in ("B3", "B3_BANDIT_NO_ALLOC"):
        return create_policy_b3(seed=seed)
    elif clean_name in ("B4", "B4_GRIDNUDGE"):
        return create_policy_b4(seed=seed)
    elif clean_name in ("B4A", "B4A_DELAY_ONLY"):
        return create_policy_b4a(seed=seed)
    elif clean_name in ("B4B", "B4B_NO_FATIGUE"):
        return create_policy_b4b(seed=seed)
    elif clean_name in ("ORACLE", "ORACLE_UPPER_BOUND"):
        return create_policy_oracle(seed=seed)
    else:
        raise ValueError(f"Unknown policy: '{name}'. Supported policies: B0, B1, B2, B3, B4, B4a, B4b, Oracle.")


def run_baseline_comparison(
    seed: int = 42,
    n_users: int = 2000,
    n_steps: int = 96,  # 1 day by default
    include_b4: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Compare baseline policies under Common Random Numbers (CRN)."""
    # Run B0
    w0 = World(seed=seed, n_users=n_users)
    res_b0 = run_simulation(world=w0, n_steps=n_steps, policy_fn=policy_b0)

    # Run B1 with identical seed
    w1 = World(seed=seed, n_users=n_users)
    res_b1 = run_simulation(world=w1, n_steps=n_steps, policy_fn=policy_b1)

    # Run B2 with identical seed
    w2 = World(seed=seed, n_users=n_users)
    res_b2 = run_simulation(world=w2, n_steps=n_steps, policy_fn=policy_b2)

    results = {
        "B0_uncontrolled": res_b0["metrics"],
        "B1_rule_based": res_b1["metrics"],
        "B2_safe_planner": res_b2["metrics"],
    }

    if include_b4:
        w4 = World(seed=seed, n_users=n_users)
        pol_b4 = create_policy_b4(seed=seed)
        res_b4 = run_simulation(world=w4, n_steps=n_steps, policy_fn=pol_b4)
        results["B4_gridnudge"] = res_b4["metrics"]

    return results

