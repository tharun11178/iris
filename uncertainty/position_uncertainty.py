"""
IRIS Position & Perception Uncertainty Calculator (Phase 9).
Estimates spatial position standard deviations (sigma_x, sigma_y) and perception uncertainty
scores based on perception detection confidence and observation quality.
"""

from typing import Tuple
from tracking.track import Track
from uncertainty.config import POSITION_UNCERTAINTY_BASE, MAX_UNCERTAINTY


def compute_position_uncertainty(track: Track, margin: float = 0.5) -> Tuple[float, float, float, float]:
    """
    Computes position standard deviations and normalized position/perception uncertainty scores.
    
    :param track: Active Track instance.
    :param margin: Object class margin offset.
    :return: Tuple containing:
             - perception_uncertainty [0.0, 1.0]
             - position_uncertainty [0.0, 1.0]
             - sigma_x (meters)
             - sigma_y (meters)
    """
    confidence = track.confidence if (track.confidence is not None and 0.0 <= track.confidence <= 1.0) else 0.5

    # Perception uncertainty is inversely related to detection confidence
    perception_unc = min(MAX_UNCERTAINTY, max(0.0, 1.0 - confidence))

    # Estimate physical position standard deviation sigma (meters)
    sigma_x = POSITION_UNCERTAINTY_BASE + perception_unc * margin
    sigma_y = POSITION_UNCERTAINTY_BASE + perception_unc * margin

    # Normalized position uncertainty score in [0.0, 1.0]
    pos_unc = min(MAX_UNCERTAINTY, (sigma_x + sigma_y) / (2.0 * (POSITION_UNCERTAINTY_BASE + margin + 1e-5)))

    return round(perception_unc, 4), round(pos_unc, 4), round(sigma_x, 4), round(sigma_y, 4)


class PositionUncertaintyEstimator:
    def __init__(self, config=None):
        self.config = config

    def estimate(self, track: Track, margin: Optional[float] = None) -> Tuple[float, float]:
        if margin is None or margin == 0.5:
            type_str = track.object_type.name if hasattr(track.object_type, "name") else str(track.object_type)
            if type_str == "CATTLE":
                margin = 1.5
            elif type_str == "PEDESTRIAN":
                margin = 1.2
            elif type_str == "MOTORCYCLE":
                margin = 1.0
            else:
                margin = 0.5
        perc_unc, pos_unc, sigma_x, sigma_y = compute_position_uncertainty(track, margin)
        return sigma_x, sigma_y

