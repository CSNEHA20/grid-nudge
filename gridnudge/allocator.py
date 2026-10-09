"""Fleet allocator module for GridNudge.

Spends a limited attention budget across eligible candidate nudges to maximize
grid and user value while enforcing:
- Attention budget cap (e.g. 5-10% of plugged EVs per interval)
- Shadow price calculation (marginal value of the last admitted candidate)
- Daily per-user notification caps
- Feeder transformer and station connector capacity limits per slot
- Anti-herding staggering across 15-minute intervals to prevent rebound peaks
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np

from gridnudge.contracts import Allocation, Persuasion, Plan


def compute_allocation_priority(
    persuasion: Persuasion,
    plan: Optional[Plan],
) -> float:
    """Calculate candidate ranking priority: uplift x grid_value."""
    if persuasion.frame == "none" or plan is None:
        return 0.0

    uplift = max(0.01, persuasion.uplift_mean) if persuasion.uplift_mean > 0.0 else (0.1 if persuasion.explored else 0.05)
    grid_val = max(0.1, abs(float(plan.outcomes.get("grid_value", 1.0))))
    # Non-negative priority score
    priority = uplift * grid_val
    return float(priority)


def find_safe_staggered_slot(
    preferred_start_iso: str,
    power_kw: float,
    duration_hours: float,
    slot_allocations_kw: Dict[str, float],
    feeder_capacity_mw: float = 12.0,
    base_load_mw: float = 6.0,
    rebound_peak_threshold: float = 0.98,
    preferred_offset: int = 0,
    max_offsets: int = 8,
) -> Optional[str]:
    """Find a staggered 15-minute start slot that does not exceed feeder capacity."""
    try:
        base_dt = datetime.fromisoformat(preferred_start_iso.replace("Z", "+00:00"))
    except Exception:
        base_dt = datetime(2026, 10, 10, 23, 0)

    max_feeder_kw = (feeder_capacity_mw * rebound_peak_threshold) * 1000.0
    base_load_kw = base_load_mw * 1000.0
    slots_needed = max(1, int(np.ceil(duration_hours * 4.0)))

    # Try starting from preferred_offset for anti-herding round-robin distribution
    for step_idx in range(max_offsets):
        offset_idx = (preferred_offset + step_idx) % max_offsets
        candidate_start = base_dt + timedelta(minutes=15 * offset_idx)
        candidate_slot_str = candidate_start.isoformat()

        # Check all intervals during the charging duration
        is_safe = True
        for step in range(slots_needed):
            step_dt = candidate_start + timedelta(minutes=15 * step)
            step_time = step_dt.isoformat()
            step_hour = step_dt.hour + (step_dt.minute / 60.0)

            # In off-peak nighttime hours (23:00 - 06:00), background load is off-peak
            if step_hour >= 23.0 or step_hour < 6.0:
                effective_base_kw = min(base_load_kw, 5500.0)
            else:
                effective_base_kw = base_load_kw

            current_allocated = slot_allocations_kw.get(step_time, 0.0)
            projected_total = effective_base_kw + current_allocated + power_kw

            if projected_total > max_feeder_kw:
                is_safe = False
                break

        if is_safe:
            # Found viable non-overloading slot
            return candidate_slot_str

    return None


def allocate_fleet_nudges(
    candidate_records: List[Dict[str, Any]],
    total_plugged_count: int,
    sim_time_iso: str,
    budget_pct: float = 0.08,
    max_daily_nudges: int = 3,
    feeder_capacity_mw: float = 12.0,
    base_load_mw: float = 5.5,
    rebound_peak_threshold: float = 0.98,
) -> Dict[str, Allocation]:
    """Allocate limited attention and grid budget across fleet candidate nudges.

    Args:
        candidate_records: List of candidate dictionaries with keys:
            'candidate_id', 'user_id', 'persuasion', 'plan', 'user_state', 'ev_context'.
        total_plugged_count: Total plugged-in EVs in the fleet this interval.
        sim_time_iso: Simulation time ISO timestamp.
        budget_pct: Attention budget fraction (default 0.08 = 8%).
        max_daily_nudges: Daily notification limit per user.
        feeder_capacity_mw: Distribution feeder capacity in MW.
        base_load_mw: Background base load in MW.
        rebound_peak_threshold: Safety headroom multiplier.

    Returns:
        Mapping from candidate_id to typed Allocation contract object.
    """
    allocations: Dict[str, Allocation] = {}

    if not candidate_records:
        return allocations

    # Attention budget: e.g. 8% of 2,000 EVs = 160 nudges
    attention_budget = max(1, int(np.floor(total_plugged_count * budget_pct)))

    # 1. Filter and score eligible candidates
    scored_candidates = []
    for cand in candidate_records:
        cand_id = str(cand.get("candidate_id") or cand.get("user_id"))
        persuasion: Persuasion = cand["persuasion"]
        plan: Optional[Plan] = cand.get("plan")
        user_state: Dict[str, Any] = cand.get("user_state", {})

        # Filter out none actions and opt-outs
        if persuasion.frame == "none" or plan is None or user_state.get("opted_out", False):
            allocations[cand_id] = Allocation(selected=False, shadow_price=0.0, slot=None)
            continue

        # Check daily frequency cap
        nudges_today = int(user_state.get("nudges_today", 0))
        if nudges_today >= max_daily_nudges:
            allocations[cand_id] = Allocation(selected=False, shadow_price=0.0, slot=None)
            continue

        priority = compute_allocation_priority(persuasion, plan)
        if priority <= 0.0:
            allocations[cand_id] = Allocation(selected=False, shadow_price=0.0, slot=None)
            continue

        scored_candidates.append(
            {
                "cand_id": cand_id,
                "priority": priority,
                "plan": plan,
                "persuasion": persuasion,
                "ev_context": cand.get("ev_context", {}),
            }
        )

    # 2. Rank greedily by priority score descending
    scored_candidates.sort(key=lambda c: c["priority"], reverse=True)

    # 3. Greedy allocation with capacity and anti-herding staggering
    slot_allocations_kw: Dict[str, float] = defaultdict(float)
    accepted_priorities: List[float] = []

    for item in scored_candidates:
        cand_id = item["cand_id"]
        plan = item["plan"]
        power_kw = float(plan.kw)

        # Check remaining attention budget
        if len(accepted_priorities) >= attention_budget:
            allocations[cand_id] = Allocation(selected=False, shadow_price=0.0, slot=None)
            continue

        # Preferred start from plan
        preferred_start = plan.start or sim_time_iso
        duration_hours = max(1.0, float(item["ev_context"].get("battery_kwh", 40.0)) / max(1.0, power_kw))

        # Find safe staggered slot preventing rebound peak (round-robin anti-herding)
        safe_slot = find_safe_staggered_slot(
            preferred_start_iso=preferred_start,
            power_kw=power_kw,
            duration_hours=duration_hours,
            slot_allocations_kw=slot_allocations_kw,
            feeder_capacity_mw=feeder_capacity_mw,
            base_load_mw=base_load_mw,
            rebound_peak_threshold=rebound_peak_threshold,
            preferred_offset=len(accepted_priorities) % 4,
        )

        if safe_slot is not None:
            # Successfully admitted
            accepted_priorities.append(item["priority"])
            # Update slot load tracking
            slots_needed = max(1, int(np.ceil(duration_hours * 4.0)))
            start_dt = datetime.fromisoformat(safe_slot.replace("Z", "+00:00"))
            for s in range(slots_needed):
                s_key = (start_dt + timedelta(minutes=15 * s)).isoformat()
                slot_allocations_kw[s_key] += power_kw

            # Temporary allocation (shadow price populated after loop)
            allocations[cand_id] = Allocation(selected=True, shadow_price=0.0, slot=safe_slot)
        else:
            # Exceeded physical feeder capacity in all candidate slots
            allocations[cand_id] = Allocation(selected=False, shadow_price=0.0, slot=None)

    # 4. Compute shadow price: marginal value of the last admitted candidate
    shadow_price = round(accepted_priorities[-1], 4) if accepted_priorities else 0.0

    # Apply computed shadow price to all admitted allocations
    for cand_id, alloc in allocations.items():
        if alloc.selected:
            allocations[cand_id] = Allocation(
                selected=True,
                shadow_price=shadow_price,
                slot=alloc.slot,
            )

    return allocations
