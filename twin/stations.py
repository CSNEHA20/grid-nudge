"""Public EV charging station hub network and queue model for the digital twin."""

from typing import Dict, List, Optional, Set


class PublicStation:
    """Represents a public DC fast-charging plaza."""

    def __init__(self, station_id: int, connectors: int = 6, connector_kw: float = 50.0):
        self.station_id = station_id
        self.connectors = connectors
        self.connector_kw = connector_kw
        self.active_evs: Set[int] = set()
        self.queue: List[int] = []
        self.is_offline: bool = False

    @property
    def effective_connectors(self) -> int:
        return 0 if self.is_offline else self.connectors

    @property
    def available_connectors(self) -> int:
        if self.is_offline:
            return 0
        return max(0, self.connectors - len(self.active_evs))

    def try_plug_in(self, ev_id: int) -> bool:
        """Attempt to plug in at the station.

        Returns True if immediately assigned a connector, False if queued.
        """
        if self.available_connectors > 0:
            self.active_evs.add(ev_id)
            return True
        else:
            if ev_id not in self.queue and ev_id not in self.active_evs:
                self.queue.append(ev_id)
            return False

    def unplug(self, ev_id: int) -> Optional[int]:
        """Unplug an EV. Advances queue if waiting vehicles exist.

        Returns the ev_id of the next vehicle assigned to a charger, if any.
        """
        if ev_id in self.active_evs:
            self.active_evs.remove(ev_id)
        if ev_id in self.queue:
            self.queue.remove(ev_id)

        next_ev = None
        if self.available_connectors > 0 and self.queue:
            next_ev = self.queue.pop(0)
            self.active_evs.add(next_ev)
        return next_ev

    def get_wait_estimate_min(self, avg_dwell_min: float = 35.0) -> float:
        """Estimate queue wait time in minutes."""
        if self.is_offline:
            return 999.0
        if self.available_connectors > 0 and len(self.queue) == 0:
            return 0.0

        # Erlang / queue approximation: queue position * avg dwell / connectors
        q_len = len(self.queue)
        c = max(1, self.connectors)
        return float((q_len + 1) * (avg_dwell_min / c))


class StationNetwork:
    """Manages the network of public fast charging stations."""

    def __init__(
        self,
        count: int = 15,
        connectors_per_station: int = 6,
        connector_kw: float = 50.0,
    ):
        self.stations: Dict[int, PublicStation] = {
            i: PublicStation(i, connectors=connectors_per_station, connector_kw=connector_kw)
            for i in range(count)
        }

    def update_outages(self, offline_ids: Set[int]) -> None:
        """Update outage statuses for stations."""
        for s_id, station in self.stations.items():
            station.is_offline = (s_id in offline_ids)

    def get_station(self, station_id: int) -> PublicStation:
        return self.stations[station_id]

    def total_active_charging_count(self) -> int:
        return sum(len(s.active_evs) for s in self.stations.values())

    def total_queued_count(self) -> int:
        return sum(len(s.queue) for s in self.stations.values())
