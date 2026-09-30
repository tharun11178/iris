"""
IRIS Decision & Emergency Safety Package (Combined Phase 13).
"""

from decision.config import (
    CRITICAL_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    MODERATE_RISK_THRESHOLD,
    LOW_RISK_THRESHOLD,
    HARD_CLEARANCE_VIOLATION,
    LOW_CLEARANCE_THRESHOLD,
    GOAL_TOLERANCE_DISTANCE,
)
from decision.decision_state import DecisionState, DecisionResult
from decision.emergency_safety import EmergencySafetyManager
from decision.decision_manager import DecisionManager

__all__ = [
    "DecisionState",
    "DecisionResult",
    "EmergencySafetyManager",
    "DecisionManager",
]
