"""
IRIS Heading Uncertainty Calculator (Phase 9).
Estimates heading uncertainty from recent track movement, correctly handling angular wrap-around
(e.g., 359 deg -> 1 deg is a 2 deg change, not 358 deg).
"""

import math
from typing import List
from tracking.track import Track
from uncertainty.config import MAX_UNCERTAINTY

STOP_SPEED_THRESHOLD: float = 0.1


def angular_difference(a1: float, a2: float) -> float:
    """
    Computes shortest signed angular difference (in radians) between two yaw angles,
    correctly handling circular 2pi boundary wrap-around.
    
    :param a1: Angle 1 in radians.
    :param a2: Angle 2 in radians.
    :return: Shortest angular difference in [-pi, pi].
    """
    return math.atan2(math.sin(a1 - a2), math.cos(a1 - a2))


def compute_heading_uncertainty(track: Track) -> float:
    """
    Computes normalized heading uncertainty score [0.0, 1.0] from track position history,
    handling circular wrap-around cleanly.
    
    :param track: Active Track instance.
    :return: Normalized heading uncertainty score.
    """
    if track.speed < STOP_SPEED_THRESHOLD:
        # Stationary object has low directional heading uncertainty
        return 0.1

    if len(track.history) < 3:
        return 0.2

    headings: List[float] = []
    for i in range(1, len(track.history)):
        dx = track.history[i][0] - track.history[i - 1][0]
        dy = track.history[i][1] - track.history[i - 1][1]
        dist = math.hypot(dx, dy)
        if dist > 0.05:
            headings.append(math.atan2(dy, dx))

    if len(headings) < 2:
        return 0.2

    # Compute angular differences handling wrap-around
    diffs = []
    for i in range(1, len(headings)):
        diff = abs(angular_difference(headings[i], headings[i - 1]))
        diffs.append(diff)

    if not diffs:
        return 0.2

    mean_diff = sum(diffs) / len(diffs)
    
    # Normalize heading uncertainty: 0 deg diff -> 0.0, pi/2 (90 deg) diff -> 1.0
    normalized_unc = min(MAX_UNCERTAINTY, mean_diff / (math.pi / 2.0))
    return round(normalized_unc, 4)


class HeadingUncertaintyEstimator:
    def __init__(self, config=None):
        self.config = config

    def estimate(self, track: Track) -> float:
        return compute_heading_uncertainty(track)

