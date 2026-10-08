"""Grid feeder, base load, solar generation, and ToU tariff model for the digital twin."""

import math
from typing import Any, Dict, Optional, Tuple


class GridFeeder:
    """Simulates a distribution feeder sub-station in Delhi."""

    def __init__(
        self,
        capacity_mw: float = 12.0,
        base_peak_mw: float = 8.5,
        base_offpeak_mw: float = 4.2,
        solar_peak_mw: float = 4.0,
        solar_peak_hour: float = 13.0,
        tariffs_config: Optional[Dict[str, Any]] = None,
    ):
        self.capacity_mw = capacity_mw
        self.base_peak_mw = base_peak_mw
        self.base_offpeak_mw = base_offpeak_mw
        self.solar_peak_mw = solar_peak_mw
        self.solar_peak_hour = solar_peak_hour
        self.tariffs_config = tariffs_config or {}

    def get_base_load_mw(self, hour_of_day: float, load_multiplier: float = 1.0) -> float:
        """Compute Delhi diurnal non-EV base load in MW.

        Mimics real Delhi Discom load shape with minimum around 04:30 and
        pronounced evening peak around 20:30.
        """
        # Multi-harmonic representation of Delhi urban demand
        t_rad = (hour_of_day / 24.0) * 2.0 * math.pi
        h1 = -math.cos(t_rad - 0.5)  # Daily wave with peak in evening
        h2 = 0.35 * -math.cos(2.0 * t_rad - 1.2)  # Secondary afternoon/evening bump
        h3 = 0.15 * -math.cos(3.0 * t_rad)

        normalized = (h1 + h2 + h3 + 1.2) / 2.4
        normalized = max(0.0, min(1.0, normalized))

        base_load = self.base_offpeak_mw + normalized * (self.base_peak_mw - self.base_offpeak_mw)
        return float(base_load * load_multiplier)

    def get_solar_generation_mw(self, hour_of_day: float, solar_multiplier: float = 1.0) -> float:
        """Compute solar PV generation in MW."""
        if hour_of_day < 6.0 or hour_of_day > 18.5:
            return 0.0

        # Gaussian solar generation curve centered at peak hour (~13:00)
        sigma = 2.4
        diff = hour_of_day - self.solar_peak_hour
        gen = self.solar_peak_mw * math.exp(-0.5 * (diff / sigma) ** 2)
        return float(max(0.0, gen * solar_multiplier))

    def get_tariff(self, hour_of_day: float, tariff_multiplier: float = 1.0) -> Tuple[str, float]:
        """Get tariff slot name and rate in INR per kWh for hour of day."""
        # Configured ToU slots:
        # Solar Hours (10:00 to 16:00): 4.50 INR/kWh
        # Evening Peak (17:00 to 23:00): 8.50 INR/kWh
        # Standard/Night (23:00 to 10:00, and 16:00 to 17:00): 6.00 INR/kWh
        if 10.0 <= hour_of_day < 16.0:
            slot = "solar_hours"
            rate = 4.50
        elif 17.0 <= hour_of_day < 23.0:
            slot = "evening_peak"
            rate = 8.50
        else:
            slot = "night_normal"
            rate = 6.00

        return slot, float(rate * tariff_multiplier)

    def compute_state(
        self,
        ev_load_mw: float,
        hour_of_day: float,
        load_multiplier: float = 1.0,
        solar_multiplier: float = 1.0,
        tariff_multiplier: float = 1.0,
    ) -> Dict[str, Any]:
        """Calculate complete grid state for the current interval."""
        base_load_mw = self.get_base_load_mw(hour_of_day, load_multiplier)
        feeder_load_mw = base_load_mw + ev_load_mw
        stress = feeder_load_mw / self.capacity_mw if self.capacity_mw > 0.0 else 0.0

        solar_mw = self.get_solar_generation_mw(hour_of_day, solar_multiplier)
        solar_share = min(1.0, solar_mw / max(feeder_load_mw, 0.1))

        tariff_slot, tariff_rate = self.get_tariff(hour_of_day, tariff_multiplier)

        is_peak = (17.0 <= hour_of_day < 23.0)
        is_green = (solar_share >= 0.20 or (10.0 <= hour_of_day < 16.0))

        return {
            "feeder_load_mw": round(feeder_load_mw, 4),
            "base_load_mw": round(base_load_mw, 4),
            "ev_load_mw": round(ev_load_mw, 4),
            "feeder_capacity_mw": self.capacity_mw,
            "stress": round(stress, 4),
            "solar_mw": round(solar_mw, 4),
            "solar_share": round(solar_share, 4),
            "tariff_slot": tariff_slot,
            "tariff_rate_inr_kwh": round(tariff_rate, 2),
            "is_peak_window": is_peak,
            "is_green_window": is_green,
        }
