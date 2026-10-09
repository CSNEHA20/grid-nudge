"""Event injector and environmental disturbance engine for the digital twin.

Simulates macro grid and weather shocks:
- Heatwave (increases evening base load and ambient temperature, raising HVAC energy)
- Solar drop (cloud cover reducing daytime PV generation)
- Station outage (reduces charging capacity across public hubs)
- Tariff change (dynamic price surge or slot shift)
"""

from typing import Any, Dict, List, Optional, Set


class EventManager:
    """Manages active and scheduled environmental events in the digital twin."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.active_events: List[Dict[str, Any]] = []
        self._load_config_events()

    def _load_config_events(self) -> None:
        """Initialize events configured in sim.yaml."""
        events_cfg = self.config.get("events", {})
        heatwave_cfg = events_cfg.get("heatwave", {})
        if heatwave_cfg.get("enabled", False):
            self.inject({
                "type": "heatwave",
                "start_step": 0,
                "end_step": 100_000,
                "temp_rise_c": float(heatwave_cfg.get("temp_rise_c", 6.0)),
                "base_load_mult": float(heatwave_cfg.get("hvac_load_multiplier", 1.18)),
            })

        solar_cfg = events_cfg.get("solar_drop", {})
        if solar_cfg.get("enabled", False):
            self.inject({
                "type": "solar_drop",
                "start_step": 0,
                "end_step": 100_000,
                "solar_factor": float(solar_cfg.get("solar_reduction_factor", 0.60)),
            })

        outage_cfg = events_cfg.get("station_outage", {})
        if outage_cfg.get("enabled", False):
            n_offline = int(outage_cfg.get("stations_offline", 2))
            self.inject({
                "type": "station_outage",
                "start_step": 0,
                "end_step": 100_000,
                "stations": list(range(n_offline)),
            })

    def inject(self, event: Dict[str, Any]) -> None:
        """Inject a disturbance event into the simulation."""
        evt = dict(event)
        evt["type"] = evt.get("type") or evt.get("event_type", "unknown")
        evt.setdefault("start_step", 0)
        evt.setdefault("end_step", 100_000)
        self.active_events.append(evt)

    def get_active_event_types(self, step: int) -> List[str]:
        """Return list of active event type names at step."""
        return [
            e["type"]
            for e in self.active_events
            if e.get("start_step", 0) <= step <= e.get("end_step", 100_000)
        ]

    def get_base_load_multiplier(self, step: int, hour_of_day: float) -> float:
        """Multiplier on grid base load from heatwaves during peak hours (16:00 to 22:00)."""
        mult = 1.0
        for e in self.active_events:
            if e["type"] == "heatwave" and e["start_step"] <= step <= e["end_step"]:
                if 16.0 <= hour_of_day <= 22.0:
                    mult *= float(e.get("base_load_mult", 1.18))
        return mult

    def get_temperature_c(self, step: int, hour_of_day: float) -> float:
        """Ambient temperature in Delhi (°C) given time of day and heatwave events."""
        # Baseline Delhi summer temperature diurnal cycle (min ~28 °C at 05:00, max ~38 °C at 15:00)
        import math
        base_temp = 33.0 + 5.0 * math.sin((hour_of_day - 9.0) * math.pi / 12.0)

        temp_rise = 0.0
        for e in self.active_events:
            if e["type"] == "heatwave" and e["start_step"] <= step <= e["end_step"]:
                temp_rise += float(e.get("temp_rise_c", 6.0))

        return float(base_temp + temp_rise)

    def get_solar_multiplier(self, step: int, hour_of_day: float) -> float:
        """Multiplier on solar generation (e.g. cloud cover drop 11:00 to 15:00)."""
        mult = 1.0
        for e in self.active_events:
            if e["type"] == "solar_drop" and e["start_step"] <= step <= e["end_step"]:
                if 11.0 <= hour_of_day <= 15.0:
                    mult *= float(e.get("solar_factor", 0.60))
        return mult

    def get_offline_stations(self, step: int) -> Set[int]:
        """Set of station IDs currently offline."""
        offline: Set[int] = set()
        for e in self.active_events:
            if e["type"] == "station_outage" and e["start_step"] <= step <= e["end_step"]:
                offline.update(e.get("stations", []))
        return offline

    def get_tariff_multiplier(self, step: int) -> float:
        """Multiplier on tariff rates."""
        mult = 1.0
        for e in self.active_events:
            if e["type"] == "tariff_change" and e["start_step"] <= step <= e["end_step"]:
                mult *= float(e.get("peak_multiplier", 1.25))
        return mult
