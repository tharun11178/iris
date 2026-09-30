"""
IRIS Emergency Safety Manager (Combined Phase 13).
Enforces hard safety overrides that supersede all efficiency goals when imminent collision,
hard clearance violations, or non-traversable path invalidations occur.
"""

import math
from typing import Tuple, Optional, Any
from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from replanning.path_state import ReplanningStatus
from decision.config import (
    CRITICAL_RISK_THRESHOLD,
    HARD_CLEARANCE_VIOLATION,
)
from decision.decision_state import DecisionState, DecisionResult


class EmergencySafetyManager:
    """
    Evaluates hard emergency safety conditions to prevent collisions and illegal road departure.
    """

    def check_emergency_stop(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        path_valid: bool = True,
        min_clearance: float = 999.0,
        peak_future_risk: float = 0.0,
        replanning_status: Optional[ReplanningStatus] = None,
        current_time: float = 0.0,
    ) -> Tuple[bool, Optional[DecisionResult]]:
        """
        Evaluates hard safety conditions. Returns (is_emergency_active, decision_result).
        """
        # 1. Replanning Safety Hold or Replan Failed -> Immediate Emergency Stop
        if replanning_status in (ReplanningStatus.SAFETY_HOLD, ReplanningStatus.REPLAN_FAILED):
            return True, DecisionResult(
                state=DecisionState.SAFETY_HOLD,
                target_speed_factor=0.0,
                explanation="EMERGENCY SAFETY: Replanning failed. Entering SAFETY_HOLD state.",
                priority_level=1,
                override_reason="NO_SAFE_REPLACEMENT_PATH",
                timestamp=current_time,
            )

        # 2. Hard Clearance Violation (< 0.8m)
        if min_clearance < HARD_CLEARANCE_VIOLATION:
            return True, DecisionResult(
                state=DecisionState.STOP,
                target_speed_factor=0.0,
                explanation=f"EMERGENCY SAFETY: Hard clearance violation ({min_clearance:.2f}m < {HARD_CLEARANCE_VIOLATION}m).",
                priority_level=1,
                override_reason="HARD_CLEARANCE_VIOLATION",
                timestamp=current_time,
            )

        # 3. Critical Future Risk / Collision Risk (> 0.85)
        if peak_future_risk >= CRITICAL_RISK_THRESHOLD:
            return True, DecisionResult(
                state=DecisionState.STOP,
                target_speed_factor=0.0,
                explanation=f"EMERGENCY SAFETY: Imminent critical collision risk ({peak_future_risk:.2f} >= {CRITICAL_RISK_THRESHOLD}).",
                priority_level=1,
                override_reason="CRITICAL_COLLISION_RISK",
                timestamp=current_time,
            )

        # 4. Invalid Active Path with No Path Points
        if not path_valid:
            return True, DecisionResult(
                state=DecisionState.STOP,
                target_speed_factor=0.0,
                explanation="EMERGENCY SAFETY: Active path invalid or non-drivable cell intersection.",
                priority_level=1,
                override_reason="INVALID_PATH",
                timestamp=current_time,
            )

        return False, None
