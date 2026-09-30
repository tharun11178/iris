"""
IRIS Prediction & Tracking Uncertainty Calculator (Phase 9).
Estimates tracking quality uncertainty and horizon-based prediction growth over time steps t.
"""

from tracking.track import Track, TrackState
from uncertainty.config import (
    HORIZON_GROWTH_RATE,
    MAX_UNCERTAINTY,
    MIN_HISTORY_FOR_LOW_UNCERTAINTY,
)


def compute_tracking_uncertainty(track: Track) -> float:
    """
    Computes normalized tracking uncertainty score [0.0, 1.0] based on track confidence,
    hits, missed frames, and track state.
    
    :param track: Active Track instance.
    :return: Normalized tracking uncertainty score.
    """
    base_unc = 1.0 - track.confidence if (0.0 <= track.confidence <= 1.0) else 0.5

    # Penalty for missed frames
    missed_penalty = track.missed_frames * 0.15

    # Discount for stable long tracks
    stability_discount = 0.2 if track.hits >= MIN_HISTORY_FOR_LOW_UNCERTAINTY else 0.0

    tracking_unc = base_unc + missed_penalty - stability_discount
    if track.state == TrackState.LOST:
        tracking_unc += 0.2

    return round(min(MAX_UNCERTAINTY, max(0.0, tracking_unc)), 4)


def compute_prediction_horizon_uncertainty(
    base_uncertainty: float,
    time_offset: float,
    growth_rate: float = HORIZON_GROWTH_RATE,
) -> float:
    """
    Computes horizon prediction uncertainty at future time offset t:
    u(t) = clamp(u_base + growth_rate * t, 0.0, 1.0).
    
    :param base_uncertainty: Initial baseline uncertainty score at t=0.
    :param time_offset: Time offset in seconds (e.g. 0.2s to 3.0s).
    :param growth_rate: Growth rate per second.
    :return: Bounded uncertainty score at time t.
    """
    val = base_uncertainty + growth_rate * time_offset
    return round(min(MAX_UNCERTAINTY, max(0.0, val)), 4)


class PredictionUncertaintyEstimator:
    def __init__(self, config=None):
        self.config = config

    def estimate(
        self,
        base_uncertainty: float,
        time_horizon: float,
        growth_rate: float = HORIZON_GROWTH_RATE,
    ) -> float:
        return compute_prediction_horizon_uncertainty(base_uncertainty, time_horizon, growth_rate)

    def estimate_tracking_uncertainty(self, track: Track) -> float:
        return compute_tracking_uncertainty(track)

