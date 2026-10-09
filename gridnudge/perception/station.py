"""Station wait and reliability perception engine using Erlang-C queueing theory.

Predicts queue wait times at arrival ETA for public charging stations based on
forecast arrival rates, average charging dwell times, and operational connector counts.
"""

import math
from typing import Any, Optional, Tuple

from gridnudge.contracts import StationView


def erlang_c_probabilities(
    lam_per_min: float,
    mu_per_min: float,
    c: int,
) -> Tuple[float, float]:
    """Compute Erlang-C queue wait probability and mean queue wait Wq in minutes.

    Args:
        lam_per_min: Arrival rate lambda in vehicles per minute.
        mu_per_min: Service rate mu in vehicles served per connector per minute.
        c: Number of operational charging connectors.

    Returns:
        Tuple of (p_wait, mean_wait_min).
    """
    if c <= 0 or mu_per_min <= 0.0 or lam_per_min <= 0.0:
        return (0.0, 0.0)

    a = lam_per_min / mu_per_min
    rho = a / c

    if rho >= 1.0:
        return (1.0, float("inf"))

    # Sum of terms for k = 0 to c - 1
    s = sum((a**k) / math.factorial(k) for k in range(c))
    top = (a**c) / (math.factorial(c) * (1.0 - rho))
    p_wait = top / (s + top)

    rate_diff = (c * mu_per_min) - lam_per_min
    mean_wait = p_wait / rate_diff if rate_diff > 0.0 else float("inf")

    return (float(p_wait), float(mean_wait))


def compute_eta_wait_quantiles(
    p_wait: float,
    lam_per_min: float,
    mu_per_min: float,
    c: int,
) -> Tuple[float, float]:
    """Compute 50th and 90th percentile wait times in minutes from Erlang-C CDF."""
    if p_wait <= 0.0 or c <= 0:
        return (0.0, 0.0)

    rate_diff = (c * mu_per_min) - lam_per_min
    if rate_diff <= 0.0:
        # Overloaded queue: bounded cap
        return (90.0, 150.0)

    # Median wait q50:
    # CDF F(t) = 1 - P(wait) * exp(-rate_diff * t) = 0.5
    if p_wait <= 0.50:
        q50 = 0.0
    else:
        q50 = math.log(2.0 * p_wait) / rate_diff

    # 90th percentile wait q90:
    if p_wait <= 0.10:
        q90 = 0.0
    else:
        q90 = math.log(10.0 * p_wait) / rate_diff

    return (round(max(0.0, q50), 2), round(max(0.0, q90), 2))


def estimate_station_wait(
    station_id: Any = 0,
    arrival_rate_per_hour: float = 8.0,
    avg_dwell_min: float = 35.0,
    connectors: int = 6,
    is_offline: bool = False,
    current_queue_len: int = 0,
    base_reliability: float = 0.95,
    eta_step: Optional[int] = None,
    **kwargs,
) -> StationView:
    """Predict queue wait quantiles and reliability for a station at vehicle ETA.

    Args:
        station_id: Station identifier.
        arrival_rate_per_hour: Predicted vehicle arrival rate at user ETA.
        avg_dwell_min: Mean session charging duration in minutes.
        connectors: Number of installed connectors.
        is_offline: Whether station is currently offline due to an outage event.
        current_queue_len: Current observed queue length if nearby.
        base_reliability: Assumed operational reliability percentage.

    Returns:
        StationView contract object.
    """
    if is_offline or connectors <= 0:
        return StationView(
            eta_wait_min_q50=99.0,
            eta_wait_min_q90=180.0,
            reliability=0.0,
        )

    lam_per_min = max(0.0, arrival_rate_per_hour / 60.0)
    mu_per_min = 1.0 / max(5.0, avg_dwell_min)

    p_wait, mean_wait = erlang_c_probabilities(lam_per_min, mu_per_min, connectors)

    if math.isinf(mean_wait):
        q50, q90 = 60.0, 120.0
    else:
        q50, q90 = compute_eta_wait_quantiles(p_wait, lam_per_min, mu_per_min, connectors)

    # If an existing queue is already present, add deterministic clearing time
    if current_queue_len > 0:
        queue_clear_min = (current_queue_len * avg_dwell_min) / connectors
        q50 += queue_clear_min
        q90 += queue_clear_min

    reliability = 0.0 if is_offline else float(min(1.0, max(0.0, base_reliability)))

    return StationView(
        eta_wait_min_q50=round(q50, 2),
        eta_wait_min_q90=round(q90, 2),
        reliability=round(reliability, 4),
    )
