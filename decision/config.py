"""
IRIS Decision Layer Configuration (Combined Phase 13).
Defines safety priority thresholds, risk levels, clearance limits, uncertainty cutoffs,
and goal arrival tolerances.
"""

# Risk thresholds
CRITICAL_RISK_THRESHOLD = 0.85
HIGH_RISK_THRESHOLD = 0.65
MODERATE_RISK_THRESHOLD = 0.40
LOW_RISK_THRESHOLD = 0.20

# Clearance thresholds (in meters)
HARD_CLEARANCE_VIOLATION = 0.8
LOW_CLEARANCE_THRESHOLD = 1.2
DESIRED_CLEARANCE = 2.0

# Uncertainty threshold
HIGH_UNCERTAINTY_THRESHOLD = 0.60

# Surface hazard severity thresholds
HIGH_SURFACE_SEVERITY = 0.60
MODERATE_SURFACE_SEVERITY = 0.35

# Goal tolerance (in meters)
GOAL_TOLERANCE_DISTANCE = 2.0

# Decision Mode
DECISION_MODE = "safety_priority"
