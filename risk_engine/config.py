"""
IRIS Risk Engine Configuration (Phase 4)
Defines risk component weights, object type safety weights, influence radii,
risk level thresholds, and debug configuration parameters.
"""

from typing import Dict

# Risk Component Weights (R_total = w_T * R_T + w_S * R_S + w_B * R_B + w_C * R_C)
TRAFFIC_RISK_WEIGHT: float = 0.35
SURFACE_RISK_WEIGHT: float = 0.25
BOUNDARY_RISK_WEIGHT: float = 0.15
COLLISION_RISK_WEIGHT: float = 0.25

# Dynamic Traffic Actor Risk Weights (Configurable prototype parameters)
OBJECT_RISK_WEIGHTS: Dict[str, float] = {
    "CAR": 0.70,
    "BUS_TRUCK": 0.80,
    "TRUCK": 0.85,
    "BUS": 0.85,
    "AUTO_RICKSHAW": 0.75,
    "MOTORCYCLE": 0.75,
    "BICYCLE": 0.80,
    "PEDESTRIAN": 0.90,
    "CATTLE": 0.95,
    "PUSHCART": 0.80,
    "OTHER": 0.75,
}

# Spatial Influence Radii (meters)
TRAFFIC_INFLUENCE_RADIUS: float = 6.0   # Meters around dynamic actor
COLLISION_INFLUENCE_RADIUS: float = 2.5 # Meters around occupied cells
BOUNDARY_INFLUENCE_DIST: float = 2.0   # Meters from road edge boundary

# Risk Level Thresholds
RISK_LEVEL_THRESHOLDS: Dict[str, float] = {
    "LOW": 0.20,
    "MODERATE": 0.40,
    "ELEVATED": 0.60,
    "HIGH": 0.80,
    "CRITICAL": 1.00,
}

# Debug Mode Toggle
RISK_DEBUG: bool = False
