"""
IRIS Motion Prediction Configuration (Phase 8).
Centralized configuration parameters and hyper-parameters for trajectory prediction,
multi-hypothesis generation, geometric prediction envelopes, and future occupancy.
"""

# Prediction horizon in seconds
PREDICTION_HORIZON: float = 3.0

# Time step step size in seconds
PREDICTION_TIME_STEP: float = 0.2

# Default motion prediction model ("constant_velocity" or "constant_acceleration")
DEFAULT_MODEL: str = "constant_velocity"

# Speed threshold in m/s below which an object is treated as stopped/stationary
STOP_SPEED_THRESHOLD: float = 0.3

# Default prediction geometric envelope margins (in meters)
PREDICTION_LATERAL_MARGIN: float = 0.5
PREDICTION_LONGITUDINAL_MARGIN: float = 0.5

# Object-class specific lateral envelope margins (in meters)
PEDESTRIAN_MARGIN: float = 1.2
MOTORCYCLE_MARGIN: float = 1.0
CATTLE_MARGIN: float = 1.2
BICYCLE_MARGIN: float = 0.8
TRUCK_MARGIN: float = 0.6
CAR_MARGIN: float = 0.5

# Linear confidence decay rate per second over prediction horizon
CONFIDENCE_DECAY_RATE: float = 0.1

# Maximum number of multi-hypotheses generated per object
MAX_HYPOTHESES: int = 3

# Whether prediction checks road boundary plausibility
ROAD_CONSTRAINT_ENABLED: bool = True

# Enable detailed motion prediction debug logs and overlays
PREDICTION_DEBUG: bool = True
