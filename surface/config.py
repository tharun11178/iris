"""
IRIS Road-Surface Intelligence Configuration Parameters (Phase 5)
Configurable thresholds, influence radii, severity scaling factors,
and traversability decision boundaries for simulated road hazards.
"""

from typing import Dict, Any

# -----------------------------------------------------------------------------
# Hazard Influence Radii (meters around hazard footprint)
# -----------------------------------------------------------------------------
SURFACE_INFLUENCE_RADII: Dict[str, float] = {
    "POTHOLE": 1.5,
    "WATERLOGGED": 2.5,
    "DEPRESSION": 1.8,
    "RAISED_SURFACE": 1.2,
    "UNEVEN_SURFACE": 2.0,
    "DEBRIS": 1.0,
    "CONSTRUCTION": 3.0,
}

# -----------------------------------------------------------------------------
# Pothole Thresholds & Severity Scaling (meters)
# -----------------------------------------------------------------------------
POTHOLE_MIN_DEPTH = 0.03            # Depth below which pothole is minor (3cm)
POTHOLE_CRITICAL_DEPTH = 0.15       # Depth above which pothole is non-traversable (15cm)
POTHOLE_TRAVERSABLE_DEPTH = 0.08    # Depth above which pothole becomes RISKY (8cm)

# -----------------------------------------------------------------------------
# Waterlogging Depth & Uncertainty Thresholds (meters)
# -----------------------------------------------------------------------------
WATER_SHALLOW_DEPTH = 0.05         # 5cm (Shallow water, CAUTION)
WATER_MODERATE_DEPTH = 0.15        # 15cm (Moderate water, RISKY)
WATER_DEEP_DEPTH = 0.30            # 30cm (Deep water, NON_TRAVERSABLE)
WATER_UNKNOWN_SURFACE_RISK_PENALTY = 0.35  # Additional risk when underlying surface is unknown

# -----------------------------------------------------------------------------
# Raised Surface / Speed Breaker Thresholds (meters)
# -----------------------------------------------------------------------------
RAISED_SAFE_HEIGHT = 0.10          # 10cm (Standard speed breaker, CAUTION)
RAISED_CRITICAL_HEIGHT = 0.25      # 25cm (Large obstacle / mound, NON_TRAVERSABLE)

# -----------------------------------------------------------------------------
# Uneven Road Roughness Thresholds (0.0 to 1.0 scale)
# -----------------------------------------------------------------------------
UNEVEN_LIGHT_ROUGHNESS = 0.3
UNEVEN_MODERATE_ROUGHNESS = 0.6
UNEVEN_SEVERE_ROUGHNESS = 0.85

# -----------------------------------------------------------------------------
# Debris Size Thresholds (meters, max footprint dimension)
# -----------------------------------------------------------------------------
DEBRIS_SMALL_SIZE = 0.5            # 50cm (Stones / small debris, CAUTION)
DEBRIS_CRITICAL_SIZE = 1.8         # 1.8m (Large rock / fallen object, NON_TRAVERSABLE)

# -----------------------------------------------------------------------------
# Default Surface Risk Weights
# -----------------------------------------------------------------------------
SURFACE_TYPE_BASE_RISK: Dict[str, float] = {
    "POTHOLE": 0.70,
    "WATERLOGGED": 0.60,
    "DEPRESSION": 0.50,
    "RAISED_SURFACE": 0.40,
    "UNEVEN_SURFACE": 0.35,
    "DEBRIS": 0.65,
    "CONSTRUCTION": 0.75,
}
