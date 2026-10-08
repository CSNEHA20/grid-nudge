"""Vectorized EV fleet generation, schedule profiles, and user state representation."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class EVUser:
    """State and parameters for an individual electric vehicle user."""

    user_id: int
    archetype: str
    battery_kwh: float
    base_wh_km: float
    has_home_charging: bool
    charger_kw: float
    commute_km: float

    # Real-time state
    soc: float
    plugged: bool = False
    charging: bool = False
    station_id: Optional[int] = None
    plug_in_step: int = -1
    departure_step: int = -1
    target_soc: float = 0.90

    # Persuasion and fatigue state
    fatigue: float = 0.0
    opted_out: bool = False
    last_frame: Optional[str] = None
    nudges_today: int = 0
    active_plan: Optional[Dict[str, Any]] = None
    delay_until_step: Optional[int] = None


class FleetManager:
    """Manages the synthetic 2,000 EV fleet in the digital twin."""

    def __init__(self, n_users: int = 2000, seed: int = 42, config: Optional[Dict[str, Any]] = None):
        self.n_users = n_users
        self.seed = seed
        self.config = config or {}
        self.rng = np.random.default_rng(seed)
        self.users: List[EVUser] = []
        self._initialize_fleet()

    def _initialize_fleet(self) -> None:
        """Vectorized generation of synthetic EV fleet with realistic archetypes."""
        archetype_probs = {
            "commuter_frugal": 0.40,
            "commuter_green": 0.20,
            "cab_driver": 0.25,
            "erratic_flex": 0.15,
        }
        names = list(archetype_probs.keys())
        probs = list(archetype_probs.values())

        # Sample archetypes
        archetypes = self.rng.choice(names, size=self.n_users, p=probs)

        # Battery capacity distribution: 30 to 60 kWh (Tata Nexon, MG ZS, BYD, etc.)
        battery_sizes = self.rng.choice([30.0, 40.5, 50.3, 60.0], size=self.n_users, p=[0.35, 0.40, 0.15, 0.10])

        # Base energy efficiency Wh/km: 140 to 180 Wh/km
        efficiencies = self.rng.uniform(140.0, 175.0, size=self.n_users)

        # Home charging availability: 75% home, 25% public
        has_home = self.rng.random(size=self.n_users) < 0.75

        # Home charger capacities: 3.3 kW (30%), 7.4 kW (60%), 11 kW (10%)
        home_kw = self.rng.choice([3.3, 7.4, 11.0], size=self.n_users, p=[0.25, 0.65, 0.10])

        # Commute daily distance
        commute_kms = np.clip(self.rng.normal(loc=38.0, scale=12.0, size=self.n_users), 15.0, 85.0)

        # Initial SOC: uniform between 0.35 and 0.75
        initial_socs = self.rng.uniform(0.35, 0.75, size=self.n_users)

        for i in range(self.n_users):
            arch = archetypes[i]
            c_kw = home_kw[i] if has_home[i] else 50.0  # 50 kW public DC fast charger
            c_km = float(commute_kms[i])
            if arch == "cab_driver":
                c_km *= 2.8  # Cab drivers drive significantly more km per day

            user = EVUser(
                user_id=i,
                archetype=arch,
                battery_kwh=float(battery_sizes[i]),
                base_wh_km=float(efficiencies[i]),
                has_home_charging=bool(has_home[i]),
                charger_kw=float(c_kw),
                commute_km=round(c_km, 1),
                soc=round(float(initial_socs[i]), 3),
            )
            self.users.append(user)

    def reset_daily_nudge_counts(self) -> None:
        """Reset daily nudge count and decay fatigue."""
        for u in self.users:
            u.nudges_today = 0
            u.fatigue = max(0.0, u.fatigue * 0.70)

    def get_candidates(self, step: int, max_nudges_per_day: int = 2) -> List[Dict[str, Any]]:
        """Return eligible candidate EVs currently plugged in and eligible for nudging."""
        candidates = []
        for u in self.users:
            if not u.plugged:
                continue
            if u.opted_out:
                continue
            if u.nudges_today >= max_nudges_per_day:
                continue
            if u.active_plan is not None:
                continue

            candidates.append({
                "user_id": u.user_id,
                "archetype": u.archetype,
                "soc": round(u.soc, 3),
                "battery_kwh": u.battery_kwh,
                "charger_kw": u.charger_kw,
                "has_home_charging": u.has_home_charging,
                "plug_in_step": u.plug_in_step,
                "departure_step": u.departure_step,
                "target_soc": u.target_soc,
                "fatigue": round(u.fatigue, 3),
                "last_frame": u.last_frame,
            })
        return candidates
