"""
IRIS Future Risk Field Configuration (Phase 10).
Centralized parameters, time discretization, risk component weights, object class risk weights,
uncertainty spread factors, and aggregation methods for the Future Risk Engine.
"""

from typing import Dict

# Time discretization for Future Risk Field horizon
FUTURE_RISK_HORIZON: float = 3.0       # Total lookahead horizon in seconds
FUTURE_RISK_TIME_STEP: float = 0.2     # Discretization step in seconds (e.g., t=0.0, 0.2, 0.4 ... 3.0)

# Baseline component risk weights for future risk combination (sum to 1.0)
TRAFFIC_RISK_WEIGHT: float = 0.35
SURFACE_RISK_WEIGHT: float = 0.25
BOUNDARY_RISK_WEIGHT: float = 0.20
COLLISION_RISK_WEIGHT: float = 0.20

# Scale factor for spatial risk expansion based on Phase 9 prediction uncertainty
UNCERTAINTY_SPREAD_SCALE: float = 1.5
MAX_UNCERTAINTY: float = 1.0

# Multi-hypothesis aggregation method ("MAX" for conservative safety engineering, or "WEIGHTED_AVERAGE")
HYPOTHESIS_AGGREGATION_METHOD: str = "MAX"

# Object class baseline prototype risk weights [0.0, 1.0]
OBJECT_RISK_WEIGHTS: Dict[str, float] = {
    "CAR": 0.80,
    "TRUCK": 0.95,
    "BUS": 0.95,
    "MOTORCYCLE": 0.85,
    "PEDESTRIAN": 0.90,
    "CATTLE": 0.90,
    "BICYCLE": 0.75,
    "PUSHCART": 0.75,
    "AUTO_RICKSHAW": 0.85,
    "OTHER": 0.70,
}

# Object class spatial influence radii (in meters)
OBJECT_INFLUENCE_RADII: Dict[str, float] = {
    "CAR": 2.5,
    "TRUCK": 4.0,
    "BUS": 4.0,
    "MOTORCYCLE": 1.8,
    "PEDESTRIAN": 1.5,
    "CATTLE": 2.2,
    "BICYCLE": 1.5,
    "PUSHCART": 2.0,
    "AUTO_RICKSHAW": 2.2,
    "OTHER": 2.0,
}

# Threshold for classifying high-risk cells
HIGH_RISK_THRESHOLD: float = 0.60

# Enable verbose logging and debug overlays for Future Risk Field
FUTURE_RISK_DEBUG: bool = True
