"""
IRIS Uncertainty Modeling Configuration (Phase 9).
Centralized configuration parameters, weights, and thresholds for position, velocity, heading,
tracking, behavior, prediction horizon, and object-specific uncertainty estimation.
"""

# Base position uncertainty in meters when observation is clean
POSITION_UNCERTAINTY_BASE: float = 0.1

# Weights for overall uncertainty aggregation (must sum to 1.0)
WEIGHT_POSITION: float = 0.15
WEIGHT_VELOCITY: float = 0.20
WEIGHT_HEADING: float = 0.15
WEIGHT_TRACKING: float = 0.15
WEIGHT_BEHAVIOR: float = 0.15
WEIGHT_PREDICTION: float = 0.20

# Growth rate of prediction uncertainty per second over time horizon
HORIZON_GROWTH_RATE: float = 0.15

# Upper bound clamp for uncertainty scores
MAX_UNCERTAINTY: float = 1.0

# Minimum track observation count for low tracking uncertainty
MIN_HISTORY_FOR_LOW_UNCERTAINTY: int = 5

# Object-specific prototype lateral uncertainty margins (in meters)
CAR_UNCERTAINTY_MARGIN: float = 0.5
TRUCK_UNCERTAINTY_MARGIN: float = 0.7
MOTORCYCLE_UNCERTAINTY_MARGIN: float = 1.0
PEDESTRIAN_UNCERTAINTY_MARGIN: float = 1.2
CATTLE_UNCERTAINTY_MARGIN: float = 1.5
BICYCLE_UNCERTAINTY_MARGIN: float = 0.8

# Enable detailed uncertainty debug overlays and logging
UNCERTAINTY_DEBUG: bool = True


class UncertaintyConfig:
    """
    Config class wrapper providing instance attribute access for uncertainty estimators.
    """

    def __init__(self):
        self.POSITION_UNCERTAINTY_BASE = POSITION_UNCERTAINTY_BASE
        self.WEIGHT_POSITION = WEIGHT_POSITION
        self.WEIGHT_VELOCITY = WEIGHT_VELOCITY
        self.WEIGHT_HEADING = WEIGHT_HEADING
        self.WEIGHT_TRACKING = WEIGHT_TRACKING
        self.WEIGHT_BEHAVIOR = WEIGHT_BEHAVIOR
        self.WEIGHT_PREDICTION = WEIGHT_PREDICTION
        self.HORIZON_GROWTH_RATE = HORIZON_GROWTH_RATE
        self.MAX_UNCERTAINTY = MAX_UNCERTAINTY
        self.MIN_HISTORY_FOR_LOW_UNCERTAINTY = MIN_HISTORY_FOR_LOW_UNCERTAINTY
        self.CAR_UNCERTAINTY_MARGIN = CAR_UNCERTAINTY_MARGIN
        self.TRUCK_UNCERTAINTY_MARGIN = TRUCK_UNCERTAINTY_MARGIN
        self.MOTORCYCLE_UNCERTAINTY_MARGIN = MOTORCYCLE_UNCERTAINTY_MARGIN
        self.PEDESTRIAN_UNCERTAINTY_MARGIN = PEDESTRIAN_UNCERTAINTY_MARGIN
        self.CATTLE_UNCERTAINTY_MARGIN = CATTLE_UNCERTAINTY_MARGIN
        self.BICYCLE_UNCERTAINTY_MARGIN = BICYCLE_UNCERTAINTY_MARGIN
        self.UNCERTAINTY_DEBUG = UNCERTAINTY_DEBUG
