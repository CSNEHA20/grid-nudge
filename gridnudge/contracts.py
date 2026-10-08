"""Data contracts and schemas for GridNudge.

DecisionRecord is the single typed contract between digital twin, perception,
planner, safety, bandit, allocator, language, outcome learning, and dashboard.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

PlanType = Literal["default", "delay", "relocate", "slow_charge", "top_up_now"]
Frame = Literal["none", "cost", "green", "battery", "convenience", "reassurance"]
Timing = Literal["at_plug_in", "plus_30m", "pre_peak"]
CedarVerdict = Literal["ALLOW", "DENY", "ERROR"]
MessageSource = Literal["llm", "template", "none"]


class Journey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    p_arrive_above_reserve: float = Field(
        ...,
        description="Calibrated probability of arriving at or above reserve SOC",
        ge=0.0,
        le=1.0,
    )
    arrival_soc_q10: float = Field(..., description="10th percentile arrival SOC", ge=0.0, le=1.0)
    arrival_soc_q50: float = Field(..., description="Median arrival SOC", ge=0.0, le=1.0)
    arrival_soc_q90: float = Field(..., description="90th percentile arrival SOC", ge=0.0, le=1.0)
    reserve_soc: float = Field(
        default=0.10,
        description="Configured reserve SOC threshold",
        ge=0.0,
        le=1.0,
    )


class BatteryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stress_score: float = Field(
        ...,
        description="Relative battery stress score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
    soh_delta_range_pct: Tuple[float, float] = Field(
        ...,
        description="Simulated relative SOH difference range percentage vs default plan",
    )


class StationView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eta_wait_min_q50: float = Field(
        ...,
        description="Median estimated wait in minutes at user ETA",
        ge=0.0,
    )
    eta_wait_min_q90: float = Field(
        ...,
        description="90th percentile estimated wait in minutes at user ETA",
        ge=0.0,
    )
    reliability: float = Field(
        ...,
        description="Assumed station operational reliability in simulation",
        ge=0.0,
        le=1.0,
    )


class GridView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stress_q50: float = Field(
        ...,
        description="Median grid stress ratio (load / capacity)",
        ge=0.0,
    )
    stress_q90: float = Field(
        ...,
        description="90th percentile grid stress ratio",
        ge=0.0,
    )
    green_window_start: Optional[str] = Field(
        default=None,
        description="Start ISO timestamp or time for green charging window",
    )
    green_window_end: Optional[str] = Field(
        default=None,
        description="End ISO timestamp or time for green charging window",
    )


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: str = Field(..., description="Unique plan identifier")
    type: PlanType = Field(..., description="Charging plan type")
    start: str = Field(..., description="ISO 8601 start time")
    kw: float = Field(..., description="Charging power in kW", ge=0.0)
    where: str = Field(..., description="Location: 'home' or station_id")
    outcomes: Dict[str, Any] = Field(
        ...,
        description="Predicted plan outcomes: cost_inr, journey_conf_lb, grid_value, battery_stress_delta, wait_min",
    )


class Safety(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invariants_ok: bool = Field(..., description="Whether all Python safety invariants passed")
    cedar: CedarVerdict = Field(..., description="AWS Cedar policy evaluation verdict")
    vetoed: List[str] = Field(
        default_factory=list,
        description="Human-readable reasons for vetoed candidate plans",
    )


class Persuasion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chosen_plan: Optional[str] = Field(
        default=None,
        description="Chosen plan_id from safe plans, or None for 'none' action",
    )
    frame: Frame = Field(..., description="Persuasion frame chosen by contextual bandit")
    timing: Optional[Timing] = Field(
        default=None,
        description="Timing of notification delivery",
    )
    uplift_mean: float = Field(
        ...,
        description="Estimated expected uplift in adoption probability",
    )
    uplift_p10: float = Field(
        ...,
        description="Conservative 10th percentile uplift estimate",
    )
    propensity: float = Field(
        ...,
        description="Action selection propensity P(a|x) logged for off-policy evaluation",
        ge=0.0,
        le=1.0,
    )
    explored: bool = Field(
        ...,
        description="Whether this action was chosen as an exploratory step",
    )


class Allocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected: bool = Field(
        ...,
        description="Whether this intervention was selected within attention and grid budget",
    )
    shadow_price: float = Field(
        ...,
        description="Marginal value shadow price at the budget cutoff",
    )
    slot: Optional[str] = Field(
        default=None,
        description="Allocated staggered charging slot start time",
    )


class Language(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Optional[str] = Field(
        default=None,
        description="Delivered message text (None if no nudge)",
    )
    facts_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured facts provided to and verified against the message",
    )
    verified: bool = Field(
        default=False,
        description="Whether all numeric claims were verified against approved facts",
    )
    source: MessageSource = Field(
        default="none",
        description="Message generation origin: llm, template, or none",
    )


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adopted: Optional[bool] = Field(
        default=None,
        description="Whether user adopted the nudged behavior",
    )
    kwh_shifted: Optional[float] = Field(
        default=None,
        description="Observed energy shifted out of peak in kWh",
    )
    opted_out: Optional[bool] = Field(
        default=None,
        description="Whether user opted out after the message",
    )
    reward: Optional[float] = Field(
        default=None,
        description="Realized causal reward value",
    )


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(..., description="Unique decision UUID or ID")
    run_id: str = Field(..., description="Simulation or operational run ID")
    sim_time: str = Field(..., description="ISO 8601 simulation timestamp")
    user_id: str = Field(..., description="Identifier for EV user / driver")
    ev: Dict[str, Any] = Field(
        ...,
        description="EV specifications (battery_kwh, current_soc, max_kw, etc.)",
    )
    journey: Optional[Journey] = Field(
        default=None,
        description="Journey confidence perception output",
    )
    battery: Optional[BatteryView] = Field(
        default=None,
        description="Battery stress perception output",
    )
    station: Optional[StationView] = Field(
        default=None,
        description="Station wait and reliability perception output",
    )
    grid: Optional[GridView] = Field(
        default=None,
        description="Grid stress and green window perception output",
    )
    plans: List[Plan] = Field(
        default_factory=list,
        description="Enumerated candidate charging plans",
    )
    safety: Safety = Field(..., description="Safety gating verification record")
    persuasion: Persuasion = Field(..., description="Bandit persuasion decision and uplift")
    allocation: Allocation = Field(..., description="Fleet allocation decision")
    language: Language = Field(
        default_factory=Language,
        description="Message generation and verification record",
    )
    outcome: Outcome = Field(
        default_factory=Outcome,
        description="Realized outcome from simulator or telematics",
    )
    fail_silent: bool = Field(
        default=False,
        description="True if an error caused graceful fallback to silence",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error details if fail_silent triggered",
    )
