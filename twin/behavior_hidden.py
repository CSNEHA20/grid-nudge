"""Hidden behavior model for the digital twin.

NEVER IMPORTED BY THE LEARNER OR ANY PERCEPTION/PLANNER MODULE.
This file represents ground-truth human decision physics inside the simulator.
All equations and parameters are documented as ASSUMED in data/ASSUMPTIONS.md.
"""

import math
from typing import Any, Dict, Optional, Tuple
import numpy as np


def sigmoid(x: float) -> float:
    """Standard numerically stable logistic sigmoid."""
    if x >= 40.0:
        return 1.0
    if x <= -40.0:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


class HiddenBehaviorEngine:
    """Evaluates human adoption of EV charging nudges."""

    def __init__(self, behavior_config: Optional[Dict[str, Any]] = None):
        self.config = behavior_config or {}
        self.archetypes = self.config.get("archetype_weights", {
            "commuter_frugal": {
                "base_shift_logit": -2.2,
                "frame_weights": {"cost": 2.4, "green": 0.1, "battery": 0.8, "convenience": 0.5, "reassurance": 0.3},
                "price_sensitivity_per_inr": 0.05,
                "fatigue_sensitivity": 0.6,
                "delay_penalty_per_hour": 0.3,
            },
            "commuter_green": {
                "base_shift_logit": -2.0,
                "frame_weights": {"cost": 0.8, "green": 1.2, "battery": 0.6, "convenience": 0.4, "reassurance": 0.5},
                "price_sensitivity_per_inr": 0.01,
                "fatigue_sensitivity": 0.4,
                "delay_penalty_per_hour": 0.4,
            },
            "cab_driver": {
                "base_shift_logit": -2.5,
                "frame_weights": {"cost": 2.8, "green": 0.0, "battery": 0.4, "convenience": 1.2, "reassurance": 0.2},
                "price_sensitivity_per_inr": 0.08,
                "fatigue_sensitivity": 0.7,
                "delay_penalty_per_hour": 0.9,
            },
            "erratic_flex": {
                "base_shift_logit": -1.8,
                "frame_weights": {"cost": 1.1, "green": 0.4, "battery": 0.5, "convenience": 0.9, "reassurance": 0.4},
                "price_sensitivity_per_inr": 0.03,
                "fatigue_sensitivity": 0.5,
                "delay_penalty_per_hour": 0.5,
            },
        })
        self.fatigue_cfg = self.config.get("fatigue", {
            "decay_rate_per_day": 0.35,
            "nudge_fatigue_penalty": 0.25,
            "ignore_decay_penalty": 0.15,
        })
        self.repeat_frame_penalty = 0.30
        self.optout_intercept = -5.0
        self.optout_per_fatigue = 0.90
        self.optout_per_repeat = 0.40

    def compute_probabilities(
        self,
        archetype: str,
        frame: str,
        savings_inr: float,
        delay_hours: float,
        fatigue: float,
        is_repeat_frame: bool,
        is_nudged: bool = True,
    ) -> Tuple[float, float, float, float]:
        """Compute P(adopt|nudge), P(adopt|none), true_uplift, and P(opt_out).

        Returns:
            Tuple of (p_adopt, p_adopt_none, true_uplift, p_opt_out)
        """
        arch_data = self.archetypes.get(archetype, self.archetypes["commuter_frugal"])
        base_logit = float(arch_data.get("base_shift_logit", -2.0))
        p_adopt_none = sigmoid(base_logit)

        if not is_nudged or frame == "none":
            return p_adopt_none, p_adopt_none, 0.0, 0.0

        frames = arch_data.get("frame_weights", {})
        frame_weight = float(frames.get(frame, 0.2))
        price_sens = float(arch_data.get("price_sensitivity_per_inr", 0.03))
        delay_penalty = float(arch_data.get("delay_penalty_per_hour", 0.4))
        fatigue_sens = float(arch_data.get("fatigue_sensitivity", 0.5))

        logit_shift = (
            base_logit
            + frame_weight
            + (price_sens * max(0.0, savings_inr))
            - (delay_penalty * max(0.0, delay_hours))
            - (fatigue_sens * fatigue)
            - (self.repeat_frame_penalty if is_repeat_frame else 0.0)
        )

        p_adopt = sigmoid(logit_shift)
        true_uplift = p_adopt - p_adopt_none

        # Opt-out probability: increases with user fatigue and repeated frames
        optout_logit = (
            self.optout_intercept
            + self.optout_per_fatigue * fatigue
            + (self.optout_per_repeat if is_repeat_frame else 0.0)
        )
        p_opt_out = sigmoid(optout_logit)

        return p_adopt, p_adopt_none, true_uplift, p_opt_out

    def evaluate_response(
        self,
        archetype: str,
        frame: str,
        savings_inr: float,
        delay_hours: float,
        current_fatigue: float,
        is_repeat_frame: bool,
        is_nudged: bool,
        rng: np.random.Generator,
    ) -> Dict[str, Any]:
        """Simulate real human behavioral response using seeded CRN stream."""
        p_adopt, p_adopt_none, true_uplift, p_opt_out = self.compute_probabilities(
            archetype=archetype,
            frame=frame,
            savings_inr=savings_inr,
            delay_hours=delay_hours,
            fatigue=current_fatigue,
            is_repeat_frame=is_repeat_frame,
            is_nudged=is_nudged,
        )

        # Draw independent common random numbers
        draw_adopt = float(rng.random())
        draw_opt_out = float(rng.random())

        adopted = bool(draw_adopt < p_adopt)
        opted_out = bool(draw_opt_out < p_opt_out) if is_nudged else False

        # Next fatigue state: decays over time, rises if nudged
        nudge_penalty = float(self.fatigue_cfg.get("nudge_fatigue_penalty", 0.25))
        new_fatigue = current_fatigue + (nudge_penalty if is_nudged else 0.0)

        return {
            "adopted": adopted,
            "opted_out": opted_out,
            "p_adopt": round(p_adopt, 4),
            "p_adopt_none": round(p_adopt_none, 4),
            "true_uplift": round(true_uplift, 4),
            "new_fatigue": round(new_fatigue, 4),
        }
