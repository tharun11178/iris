"""
IRIS Velocity Uncertainty Calculator (Phase 9).
Estimates velocity uncertainty from historical position variations and velocity variance.
"""

import math
from typing import List, Tuple
from tracking.track import Track
from uncertainty.config import MAX_UNCERTAINTY


def compute_velocity_uncertainty(track: Track) -> float:
    """
    Computes normalized velocity uncertainty score [0.0, 1.0] from track position history variance.
    
    :param track: Active Track instance.
    :return: Normalized velocity uncertainty score.
    """
    if len(track.history) < 3:
        # Insufficient history -> default moderate baseline uncertainty
        return 0.3

    # Calculate frame-to-frame velocity components over history
    velocities: List[Tuple[float, float]] = []
    dt_nominal = 0.1  # Nominal frame step

    for i in range(1, len(track.history)):
        dx = track.history[i][0] - track.history[i - 1][0]
        dy = track.history[i][1] - track.history[i - 1][1]
        velocities.append((dx / dt_nominal, dy / dt_nominal))

    if not velocities:
        return 0.3

    mean_vx = sum(v[0] for v in velocities) / len(velocities)
    mean_vy = sum(v[1] for v in velocities) / len(velocities)

    var_vx = sum((v[0] - mean_vx) ** 2 for v in velocities) / len(velocities)
    var_vy = sum((v[1] - mean_vy) ** 2 for v in velocities) / len(velocities)

    std_v = math.sqrt(var_vx + var_vy)

    # Normalize std_v to [0.0, 1.0] using a scaling factor of 5.0 m/s std dev
    normalized_unc = min(MAX_UNCERTAINTY, std_v / 5.0)
    return round(normalized_unc, 4)


class VelocityUncertaintyEstimator:
    def __init__(self, config=None):
        self.config = config

    def estimate(self, track: Track) -> float:
        return compute_velocity_uncertainty(track)

