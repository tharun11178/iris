"""
IRIS Safe-Space / Negative-Space Planner Configuration (Phase 11).
Centralized parameters, local planning window radius, vehicle safety margins,
multi-objective cost weights, candidate sampling distance, and planner mode flags.
"""

# Local planning window radius around ego vehicle (in meters)
LOCAL_PLANNING_RADIUS: float = 40.0

# Vehicle physical dimensions & safety clearances (in meters)
VEHICLE_WIDTH: float = 1.8
VEHICLE_LENGTH: float = 4.2
VEHICLE_SAFETY_MARGIN: float = 0.4  # Lateral buffer margin around vehicle
MIN_CORRIDOR_WIDTH: float = VEHICLE_WIDTH + VEHICLE_SAFETY_MARGIN  # 2.2m threshold

# Candidate Scorer Multi-Objective Cost Weights (prototype parameters)
RISK_COST_WEIGHT: float = 0.30        # Weight for spatiotemporal future risk integral & peak risk
CLEARANCE_COST_WEIGHT: float = 0.15   # Weight for inverse clearance proximity cost
LENGTH_COST_WEIGHT: float = 0.10      # Weight for path length efficiency cost
SMOOTHNESS_COST_WEIGHT: float = 0.10  # Weight for path geometric curvature & heading change
SURFACE_COST_WEIGHT: float = 0.15     # Weight for road surface hazard severity cost
BOUNDARY_COST_WEIGHT: float = 0.10    # Weight for road edge proximity cost
UNCERTAINTY_COST_WEIGHT: float = 0.05 # Weight for Phase 9 prediction uncertainty cost
GOAL_COST_WEIGHT: float = 0.05        # Weight for goal distance cost

# Candidate Generation Parameters
MAX_CANDIDATES: int = 5
CANDIDATE_SAMPLE_DISTANCE: float = 0.5  # Spatial sampling step along candidate path (in meters)
NOMINAL_PLANNING_SPEED: float = 7.0     # Nominal travel speed for temporal arrival time estimation (m/s)

# Planner Modes
PLANNER_MODE: str = "iris_safe_space"  # "baseline_astar" vs "iris_safe_space"

# Connected Component Neighborhood ("4" or "8")
CONNECTED_NEIGHBORHOOD: int = 8

# Debug overlay and console output flags
SAFE_SPACE_DEBUG: bool = True
