"""
IRIS Safe-Space / Negative-Space Planner Package (Phase 11).
Provides drivable negative-space detection, clearance mapping, candidate corridor generation,
multi-objective cost scoring, and the SafeSpacePlanner facade.
"""

from .config import (
    LOCAL_PLANNING_RADIUS,
    VEHICLE_SAFETY_MARGIN,
    MIN_CORRIDOR_WIDTH,
    RISK_COST_WEIGHT,
    CLEARANCE_COST_WEIGHT,
    LENGTH_COST_WEIGHT,
    SMOOTHNESS_COST_WEIGHT,
    SURFACE_COST_WEIGHT,
    BOUNDARY_COST_WEIGHT,
    UNCERTAINTY_COST_WEIGHT,
    GOAL_COST_WEIGHT,
    PLANNER_MODE,
)
from .free_space import FreeSpaceRegion, FreeSpaceDetector
from .clearance import ClearanceMap
from .corridor import SafeCorridor
from .candidate_generator import CandidateGenerator
from .candidate_scorer import CandidateScorer
from .safe_space_analyzer import SafeSpaceMap, SafeSpaceAnalyzer
from .safe_space_planner import PlanningResult, SafeSpacePlanner

__all__ = [
    "LOCAL_PLANNING_RADIUS",
    "VEHICLE_SAFETY_MARGIN",
    "MIN_CORRIDOR_WIDTH",
    "RISK_COST_WEIGHT",
    "CLEARANCE_COST_WEIGHT",
    "LENGTH_COST_WEIGHT",
    "SMOOTHNESS_COST_WEIGHT",
    "SURFACE_COST_WEIGHT",
    "BOUNDARY_COST_WEIGHT",
    "UNCERTAINTY_COST_WEIGHT",
    "GOAL_COST_WEIGHT",
    "PLANNER_MODE",
    "FreeSpaceRegion",
    "FreeSpaceDetector",
    "ClearanceMap",
    "SafeCorridor",
    "CandidateGenerator",
    "CandidateScorer",
    "SafeSpaceMap",
    "SafeSpaceAnalyzer",
    "PlanningResult",
    "SafeSpacePlanner",
]
