"""
IRIS Speed Controller (Combined Phase 13).
Regulates vehicle target speed based on DecisionState, Future Risk, Minimum Clearance,
Surface Hazard Severity, Uncertainty, and Path Curvature.
"""

import math
from typing import Optional, Any
from control.config import (
    MAX_SPEED,
    NOMINAL_TARGET_SPEED,
    CAUTION_SPEED,
    SLOW_SPEED,
    MIN_SPEED,
)
from decision.decision_state import DecisionState


class SpeedController:
    """
    Computes smooth, safe target speed commands based on environmental risk factors and decision states.
    """

    def compute_target_speed(
        self,
        current_speed: float,
        decision_state: DecisionState,
        future_risk: float = 0.0,
        minimum_clearance: float = 999.0,
        surface_severity: float = 0.0,
        uncertainty: float = 0.0,
        target_speed_factor: float = 1.0,
    ) -> float:
        """
        Calculates actionable target speed command in m/s bounded by [MIN_SPEED, MAX_SPEED].
        """
        # 1. Decision State Base Speed Target
        if decision_state in (DecisionState.STOP, DecisionState.SAFETY_HOLD, DecisionState.GOAL_REACHED):
            return 0.0

        if decision_state == DecisionState.SLOW_DOWN:
            base_target = SLOW_SPEED
        elif decision_state == DecisionState.CAUTION:
            base_target = CAUTION_SPEED
        elif decision_state == DecisionState.REPLAN:
            base_target = CAUTION_SPEED * 0.9
        else:
            base_target = NOMINAL_TARGET_SPEED * max(0.1, target_speed_factor)

        # 2. Risk & Environmental Risk Scaling Factors
        # Risk factor: Reduces speed exponentially as risk approaches 1.0
        risk_scale = max(0.2, 1.0 - 0.7 * future_risk)

        # Clearance factor: Reduces speed when side clearance is tight (< 2.0m)
        if minimum_clearance < 0.8:
            clearance_scale = 0.0
        elif minimum_clearance < 1.5:
            clearance_scale = max(0.3, (minimum_clearance - 0.8) / 0.7)
        else:
            clearance_scale = 1.0

        # Surface severity factor: Slow down for severe potholes/waterlogging
        surface_scale = max(0.3, 1.0 - 0.8 * surface_severity)

        # Uncertainty scaling
        unc_scale = max(0.5, 1.0 - 0.5 * uncertainty)

        # Aggregate combined safe speed
        combined_scale = min(risk_scale, clearance_scale, surface_scale, unc_scale)
        target_v = base_target * combined_scale

        # Clamp target speed to valid bounds
        target_v = max(MIN_SPEED, min(MAX_SPEED, target_v))
        return float(target_v)
