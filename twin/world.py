"""Digital twin world simulation engine.

This is the central execution environment for GridNudge.
It coordinates EV users, grid feeders, charging stations, environmental events,
and the hidden human behavioral response model.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import numpy as np
import yaml

from twin.battery_truth import charge_step, discharge_step
from twin.behavior_hidden import HiddenBehaviorEngine
from twin.events import EventManager
from twin.grid import GridFeeder
from twin.stations import StationNetwork
from twin.users import FleetManager


def compute_kwh_shifted_from_peak(
    plan_type: str,
    adopted: bool,
    initial_soc: float,
    target_soc: float,
    battery_kwh: float,
    nominal_charger_kw: float,
    plug_in_step: int,
    delay_hours: float = 3.5,
    efficiency: float = 0.92,
) -> float:
    """Compute physical kWh moved out of the evening peak window (18:00 - 22:00, steps 72 - 88)."""
    if not adopted or plan_type in ("default", "top_up_now"):
        return 0.0

    needed_kwh = max(0.0, (target_soc - initial_soc) * battery_kwh)
    if needed_kwh <= 0.0 or nominal_charger_kw <= 0.0:
        return 0.0

    day_start = (plug_in_step // 96) * 96
    peak_start = day_start + 72  # 18:00
    peak_end = day_start + 88    # 22:00

    # Default charging trajectory
    dur_default_hrs = needed_kwh / (nominal_charger_kw * efficiency)
    end_default_step = plug_in_step + int(np.ceil(dur_default_hrs * 4.0))

    overlap_default_steps = max(0, min(end_default_step, peak_end) - max(plug_in_step, peak_start))
    kwh_peak_default = min(needed_kwh, overlap_default_steps * 0.25 * nominal_charger_kw * efficiency)

    if kwh_peak_default <= 0.0:
        return 0.0

    if plan_type == "delay":
        delay_steps = int(delay_hours * 4.0)
        delay_start_step = plug_in_step + delay_steps
        delay_end_step = delay_start_step + int(np.ceil(dur_default_hrs * 4.0))

        overlap_delay_steps = max(0, min(delay_end_step, peak_end) - max(delay_start_step, peak_start))
        kwh_peak_delay = min(needed_kwh, overlap_delay_steps * 0.25 * nominal_charger_kw * efficiency)
        return round(float(max(0.0, kwh_peak_default - kwh_peak_delay)), 2)

    elif plan_type == "slow_charge":
        slow_kw = max(2.0, nominal_charger_kw * 0.5)
        dur_slow_hrs = needed_kwh / (slow_kw * efficiency)
        slow_end_step = plug_in_step + int(np.ceil(dur_slow_hrs * 4.0))

        overlap_slow_steps = max(0, min(slow_end_step, peak_end) - max(plug_in_step, peak_start))
        kwh_peak_slow = min(needed_kwh, overlap_slow_steps * 0.25 * slow_kw * efficiency)
        return round(float(max(0.0, kwh_peak_default - kwh_peak_slow)), 2)

    elif plan_type == "relocate":
        return round(float(kwh_peak_default), 2)

    return 0.0


class World:
    """The digital twin EV-energy simulation environment."""

    def __init__(
        self,
        seed: int = 42,
        n_users: int = 2000,
        step_minutes: int = 15,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.seed = seed
        self.n_users = n_users
        self.step_minutes = step_minutes
        self.config = config or self._load_default_configs()

        # Initialize simulation sub-systems
        self.events = EventManager(self.config.get("sim", {}))
        self.grid = GridFeeder(
            capacity_mw=float(self.config.get("sim", {}).get("grid", {}).get("feeder_capacity_mw", 12.0)),
            base_peak_mw=float(self.config.get("sim", {}).get("grid", {}).get("base_peak_mw", 8.5)),
            base_offpeak_mw=float(self.config.get("sim", {}).get("grid", {}).get("base_offpeak_mw", 4.2)),
            solar_peak_mw=float(self.config.get("sim", {}).get("grid", {}).get("solar_peak_mw", 4.0)),
            solar_peak_hour=float(self.config.get("sim", {}).get("grid", {}).get("solar_peak_hour", 13.0)),
            tariffs_config=self.config.get("tariffs", {}),
        )
        self.stations = StationNetwork(
            count=int(self.config.get("sim", {}).get("stations", {}).get("count", 15)),
            connectors_per_station=int(self.config.get("sim", {}).get("stations", {}).get("connectors_per_station", 6)),
            connector_kw=float(self.config.get("sim", {}).get("stations", {}).get("connector_kw", 50.0)),
        )
        self.fleet = FleetManager(n_users=self.n_users, seed=self.seed, config=self.config.get("sim", {}))
        self.behavior = HiddenBehaviorEngine(self.config.get("behavior", {}))

        self.current_step = 0
        self.start_datetime = datetime(2026, 10, 8, 0, 0, 0)
        self.pending_outcomes: List[Dict[str, Any]] = []
        self.closed_outcomes: List[Dict[str, Any]] = []
        self.all_outcomes: List[Dict[str, Any]] = []
        self.stranded_any_count = 0
        self.stranded_attributable_count = 0

    def _load_default_configs(self) -> Dict[str, Any]:
        """Load configuration files from config directory if not provided."""
        cfg = {"sim": {}, "behavior": {}, "tariffs": {}}
        try:
            with open("config/sim.yaml", "r", encoding="utf-8") as f:
                cfg["sim"] = yaml.safe_load(f) or {}
        except Exception:
            pass
        try:
            with open("config/behavior_assumed.yaml", "r", encoding="utf-8") as f:
                cfg["behavior"] = yaml.safe_load(f) or {}
        except Exception:
            pass
        try:
            with open("config/tariffs.yaml", "r", encoding="utf-8") as f:
                cfg["tariffs"] = yaml.safe_load(f) or {}
        except Exception:
            pass
        return cfg

    def get_user_rng(self, user_id: int, step: int) -> np.random.Generator:
        """Create reproducible seeded CRN stream for a specific (seed, user_id, step)."""
        seed_int = int((self.seed * 1_000_003 + user_id * 10_007 + step) % (2**31 - 1))
        return np.random.default_rng(seed_int)

    @property
    def current_time(self) -> datetime:
        return self.start_datetime + timedelta(minutes=self.current_step * self.step_minutes)

    @property
    def hour_of_day(self) -> float:
        step_of_day = self.current_step % 96
        return (step_of_day * self.step_minutes) / 60.0

    def candidates(self) -> List[Dict[str, Any]]:
        """Return eligible candidate EVs currently plugged in and eligible for persuasion."""
        return self.fleet.get_candidates(self.current_step)

    def grid_state(self) -> Dict[str, Any]:
        """Return the current feeder and grid telemetry state."""
        load_mult = self.events.get_base_load_multiplier(self.current_step, self.hour_of_day)
        solar_mult = self.events.get_solar_multiplier(self.current_step, self.hour_of_day)
        tariff_mult = self.events.get_tariff_multiplier(self.current_step)

        # Calculate current fleet EV charging power in MW
        ev_kw_total = sum(
            (u.charger_kw_cap if u.charger_kw_cap is not None else u.charger_kw)
            for u in self.fleet.users
            if u.plugged and u.charging
        )
        ev_load_mw = ev_kw_total / 1000.0

        state = self.grid.compute_state(
            ev_load_mw=ev_load_mw,
            hour_of_day=self.hour_of_day,
            load_multiplier=load_mult,
            solar_multiplier=solar_mult,
            tariff_multiplier=tariff_mult,
        )
        state["step"] = self.current_step
        state["sim_time"] = self.current_time.isoformat()
        state["active_events"] = self.events.get_active_event_types(self.current_step)
        return state

    def inject(self, event: Dict[str, Any]) -> None:
        """Inject an environmental disturbance event."""
        self.events.inject(event)
        # Update station outages if outage event
        offline = self.events.get_offline_stations(self.current_step)
        self.stations.update_outages(offline)

    def apply_decisions(self, decisions: List[Dict[str, Any]]) -> None:
        """Apply nudge decisions to candidate vehicles using the hidden behavior model.

        Evaluates human adoption under Common Random Numbers (CRN).
        """
        for d in decisions:
            user_id = d.get("user_id")
            if user_id is None or user_id >= len(self.fleet.users):
                continue

            user = self.fleet.users[user_id]
            if not user.plugged or user.opted_out:
                continue

            plan = d.get("plan", {})
            plan_type = plan.get("type", "default") if isinstance(plan, dict) else str(plan)
            frame = d.get("frame", "none")
            decision_id = d.get("decision_id", f"d_{self.current_step}_{user_id}")

            is_nudged = (frame != "none" and plan_type != "default")

            # Determine financial and delay parameters
            savings_inr = float(d.get("savings_inr", 0.0))
            if savings_inr <= 0.0 and plan_type == "delay":
                # Default saving estimate from tariff shift: ~30 kWh * (8.5 - 6.0) = 75 INR
                savings_inr = 65.0

            delay_hours = float(d.get("delay_hours", 2.5 if plan_type == "delay" else 0.0))
            is_repeat = (user.last_frame == frame and frame != "none")

            # Evaluate hidden human response with seeded CRN stream
            user_rng = self.get_user_rng(user_id, self.current_step)
            resp = self.behavior.evaluate_response(
                archetype=user.archetype,
                frame=frame,
                savings_inr=savings_inr,
                delay_hours=delay_hours,
                current_fatigue=user.fatigue,
                is_repeat_frame=is_repeat,
                is_nudged=is_nudged,
                rng=user_rng,
            )

            user.fatigue = resp["new_fatigue"]
            if resp["opted_out"]:
                user.opted_out = True

            if is_nudged:
                user.nudges_today += 1
                user.last_frame = frame

            adopted = resp["adopted"]
            window_end_step = min(user.departure_step, self.current_step + 4)

            if adopted and plan_type == "delay":
                # Delay charging start until off-peak slot (e.g. 23:00)
                delay_steps = int(delay_hours * (60.0 / self.step_minutes))
                user.delay_until_step = self.current_step + delay_steps
                user.active_plan = plan if isinstance(plan, dict) else {"type": plan_type}
                user.charging = False
                user.session_had_adopted_nudge = True
            elif adopted and plan_type == "slow_charge":
                nominal_kw = user.nominal_charger_kw if user.nominal_charger_kw is not None else user.charger_kw
                user.charger_kw_cap = max(2.0, nominal_kw * 0.5)
                user.charger_kw = user.charger_kw_cap
                user.active_plan = {"type": "slow_charge", "charger_kw_cap": user.charger_kw_cap}
                user.session_had_adopted_nudge = True
            elif is_nudged and not adopted and not decision_id.startswith("b1_"):
                # Respectful policy (B2/B4): do not spam candidate again if they rejected
                user.active_plan = {"type": "default"}

            # Record outcome tracker
            self.pending_outcomes.append({
                "decision_id": decision_id,
                "user_id": user_id,
                "window_end_step": window_end_step,
                "plan_type": plan_type,
                "frame": frame,
                "is_nudged": is_nudged,
                "adopted": adopted,
                "savings_inr": savings_inr if adopted else 0.0,
                "delay_hours": delay_hours,
                "true_uplift": resp["true_uplift"],
                "opted_out": resp["opted_out"],
                "initial_soc": user.soc,
                "target_soc": user.target_soc,
                "battery_kwh": user.battery_kwh,
                "nominal_charger_kw": user.nominal_charger_kw or user.charger_kw,
                "plug_in_step": user.plug_in_step,
            })

    def _update_schedules_and_arrivals(self) -> None:
        """Update EV commutes, arrivals, plug-in, and departure state."""
        step_of_day = self.current_step % 96

        # Daily reset of nudge counts at midnight (step_of_day == 0)
        if step_of_day == 0:
            self.fleet.reset_daily_nudge_counts()

        # Commuter arrival wave: 18:00 to 19:30 (steps 72 to 78)
        # Cab driver wave: 14:00 (step 56) and 23:30 (step 94)
        for u in self.fleet.users:
            if not u.plugged:
                should_plug = False
                arrival_jitter = (u.user_id % 7)

                if u.archetype in ("commuter_frugal", "commuter_green"):
                    if step_of_day == 72 + arrival_jitter:
                        should_plug = True
                        # Driving trip discharge before arrival
                        _, _ = discharge_step(
                            soc=u.soc,
                            battery_kwh=u.battery_kwh,
                            distance_km=u.commute_km * 0.5,
                            base_wh_km=u.base_wh_km,
                            traffic_factor=1.1,
                            driver_factor=1.0,
                            hvac_kw=1.5 if self.events.get_temperature_c(self.current_step, self.hour_of_day) > 35 else 0.5,
                        )
                elif u.archetype == "cab_driver":
                    if step_of_day in (56 + (u.user_id % 4), 92 + (u.user_id % 4)):
                        should_plug = True
                        _, _ = discharge_step(
                            soc=u.soc,
                            battery_kwh=u.battery_kwh,
                            distance_km=u.commute_km * 0.4,
                            base_wh_km=u.base_wh_km,
                        )
                else:  # erratic_flex
                    if step_of_day == 64 + (u.user_id % 16):
                        should_plug = True
                        _, _ = discharge_step(
                            soc=u.soc,
                            battery_kwh=u.battery_kwh,
                            distance_km=u.commute_km * 0.5,
                            base_wh_km=u.base_wh_km,
                        )

                if should_plug:
                    u.plugged = True
                    u.plug_in_step = self.current_step
                    # Default departure is next morning (~07:30 = 30 steps after midnight)
                    steps_until_morning = (96 - step_of_day) + 30
                    u.departure_step = self.current_step + max(20, steps_until_morning)
                    u.charging = True
                    u.active_plan = None
                    u.delay_until_step = None
                    u.charger_kw = u.nominal_charger_kw if u.nominal_charger_kw is not None else u.charger_kw
                    u.charger_kw_cap = None
                    u.session_had_adopted_nudge = False

            elif u.plugged:
                # Check departure deadline
                if self.current_step >= u.departure_step:
                    # Check departure SOC against commute trip requirement + 10% reserve
                    needed_energy_kwh = (u.commute_km * 0.5 * u.base_wh_km) / 1000.0
                    reserve_kwh = u.battery_kwh * 0.10
                    soc_kwh = u.soc * u.battery_kwh
                    if soc_kwh < (needed_energy_kwh + reserve_kwh):
                        self.stranded_any_count += 1
                        if getattr(u, "session_had_adopted_nudge", False):
                            self.stranded_attributable_count += 1

                    u.plugged = False
                    u.charging = False
                    u.active_plan = None
                    u.delay_until_step = None
                    u.charger_kw = u.nominal_charger_kw if u.nominal_charger_kw is not None else u.charger_kw
                    u.charger_kw_cap = None
                    u.session_had_adopted_nudge = False
                    # Morning commute discharge
                    u.soc, _ = discharge_step(
                        soc=u.soc,
                        battery_kwh=u.battery_kwh,
                        distance_km=u.commute_km * 0.5,
                        base_wh_km=u.base_wh_km,
                    )

    def step(self) -> Dict[str, Any]:
        """Advance the simulation by one interval (15 minutes)."""
        step_hours = self.step_minutes / 60.0

        # Update offline stations from events
        offline_stations = self.events.get_offline_stations(self.current_step)
        self.stations.update_outages(offline_stations)

        # 1. Update vehicle schedules, arrivals, departures
        self._update_schedules_and_arrivals()

        # 2. Charge active vehicles
        total_ev_kw = 0.0
        total_kwh_delivered = 0.0
        plugged_count = 0
        charging_count = 0

        for u in self.fleet.users:
            if not u.plugged:
                continue

            plugged_count += 1

            # Check if charging is delayed
            if u.delay_until_step is not None and self.current_step < u.delay_until_step:
                u.charging = False
                continue

            # Target reached?
            if u.soc >= u.target_soc:
                u.charging = False
                continue

            # Vehicle is actively charging
            u.charging = True
            charging_count += 1

            kw_cap = u.charger_kw_cap if u.charger_kw_cap is not None else u.charger_kw
            new_soc, kw_drawn, kwh_del = charge_step(
                soc=u.soc,
                battery_kwh=u.battery_kwh,
                charger_kw=kw_cap,
                step_hours=step_hours,
                efficiency=0.92,
                target_soc=u.target_soc,
            )
            u.soc = new_soc
            total_ev_kw += kw_drawn
            total_kwh_delivered += kwh_del

        ev_load_mw = total_ev_kw / 1000.0

        # 3. Calculate grid state
        load_mult = self.events.get_base_load_multiplier(self.current_step, self.hour_of_day)
        solar_mult = self.events.get_solar_multiplier(self.current_step, self.hour_of_day)
        tariff_mult = self.events.get_tariff_multiplier(self.current_step)

        grid_telemetry = self.grid.compute_state(
            ev_load_mw=ev_load_mw,
            hour_of_day=self.hour_of_day,
            load_multiplier=load_mult,
            solar_multiplier=solar_mult,
            tariff_multiplier=tariff_mult,
        )

        # 4. Check and close expired outcome windows
        remaining_outcomes = []
        for o in self.pending_outcomes:
            if self.current_step >= o["window_end_step"]:
                user = self.fleet.users[o["user_id"]]
                kwh_shifted = compute_kwh_shifted_from_peak(
                    plan_type=o["plan_type"],
                    adopted=o["adopted"],
                    initial_soc=o["initial_soc"],
                    target_soc=o.get("target_soc", user.target_soc),
                    battery_kwh=o.get("battery_kwh", user.battery_kwh),
                    nominal_charger_kw=o.get("nominal_charger_kw", user.nominal_charger_kw or user.charger_kw),
                    plug_in_step=o["plug_in_step"],
                    delay_hours=o.get("delay_hours", 3.5),
                )
                stress_delta = -0.05 if (o["adopted"] and o["plan_type"] in ("delay", "slow_charge")) else 0.0

                closed = {
                    "decision_id": o["decision_id"],
                    "user_id": o["user_id"],
                    "is_nudged": o.get("is_nudged", True),
                    "plan_type": o["plan_type"],
                    "frame": o.get("frame", "none"),
                    "adopted": o["adopted"],
                    "initial_soc": o["initial_soc"],
                    "kwh_shifted": kwh_shifted,
                    "kwh_shifted_from_peak": kwh_shifted,
                    "savings_inr": o["savings_inr"],
                    "battery_stress_delta": stress_delta,
                    "opted_out": o["opted_out"],
                    "realized_value": round(kwh_shifted * 2.5 + o["savings_inr"] * 0.1, 2),
                    "true_uplift": o["true_uplift"],
                }
                self.closed_outcomes.append(closed)
                self.all_outcomes.append(closed)
            else:
                remaining_outcomes.append(o)
        self.pending_outcomes = remaining_outcomes

        # Advance step counter
        self.current_step += 1

        telemetry = {
            "step": self.current_step - 1,
            "sim_time": self.current_time.isoformat(),
            "day": (self.current_step - 1) // 96,
            "hour_of_day": round(self.hour_of_day, 2),
            "feeder_load_mw": grid_telemetry["feeder_load_mw"],
            "base_load_mw": grid_telemetry["base_load_mw"],
            "ev_load_mw": grid_telemetry["ev_load_mw"],
            "grid_stress": grid_telemetry["stress"],
            "solar_share": grid_telemetry["solar_share"],
            "solar_mw": grid_telemetry["solar_mw"],
            "tariff_slot": grid_telemetry["tariff_slot"],
            "tariff_rate_inr_kwh": grid_telemetry["tariff_rate_inr_kwh"],
            "plugged_evs": plugged_count,
            "charging_evs": charging_count,
            "energy_kwh_delivered": round(total_kwh_delivered, 2),
            "active_events": self.events.get_active_event_types(self.current_step - 1),
        }
        return telemetry

    def pop_outcomes(self) -> List[Dict[str, Any]]:
        """Return and clear outcomes whose window closed."""
        outcomes = self.closed_outcomes
        self.closed_outcomes = []
        return outcomes

    def flush_pending_outcomes(self) -> List[Dict[str, Any]]:
        """Force-resolve and return any remaining pending outcomes at simulation end."""
        closed = []
        for o in self.pending_outcomes:
            user = self.fleet.users[o["user_id"]]
            kwh_shifted = compute_kwh_shifted_from_peak(
                plan_type=o["plan_type"],
                adopted=o["adopted"],
                initial_soc=o["initial_soc"],
                target_soc=o.get("target_soc", user.target_soc),
                battery_kwh=o.get("battery_kwh", user.battery_kwh),
                nominal_charger_kw=o.get("nominal_charger_kw", user.nominal_charger_kw or user.charger_kw),
                plug_in_step=o["plug_in_step"],
                delay_hours=o.get("delay_hours", 3.5),
            )
            stress_delta = -0.05 if (o["adopted"] and o["plan_type"] in ("delay", "slow_charge")) else 0.0
            rec = {
                "decision_id": o["decision_id"],
                "user_id": o["user_id"],
                "is_nudged": o.get("is_nudged", True),
                "plan_type": o["plan_type"],
                "frame": o.get("frame", "none"),
                "adopted": o["adopted"],
                "initial_soc": o["initial_soc"],
                "kwh_shifted": kwh_shifted,
                "kwh_shifted_from_peak": kwh_shifted,
                "savings_inr": o["savings_inr"],
                "battery_stress_delta": stress_delta,
                "opted_out": o["opted_out"],
                "realized_value": round(kwh_shifted * 2.5 + o["savings_inr"] * 0.1, 2),
                "true_uplift": o["true_uplift"],
            }
            closed.append(rec)
            self.all_outcomes.append(rec)
        self.pending_outcomes = []
        return closed

    def get_provenance(self) -> Dict[str, str]:
        """Return dataset provenance metadata for auditability."""
        from twin.data_loader import get_data_provenance
        return get_data_provenance()
