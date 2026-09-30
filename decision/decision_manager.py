"""
IRIS Decision Manager Facade (Combined Phase 13).
Evaluates safety priority hierarchy using world model, future risk field, uncertainty,
surface hazards, active path health, and goal proximity to output actionable DecisionResult.
"""

import math
from typing import Tuple, Optional, Any, List
from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from replanning.replanning_manager import ReplanningManager
from replanning.path_state import ReplanningStatus, CurrentPathState
from decision.config import (
    CRITICAL_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    MODERATE_RISK_THRESHOLD,
    HARD_CLEARANCE_VIOLATION,
    LOW_CLEARANCE_THRESHOLD,
    HIGH_UNCERTAINTY_THRESHOLD,
    HIGH_SURFACE_SEVERITY,
    MODERATE_SURFACE_SEVERITY,
    GOAL_TOLERANCE_DISTANCE,
)
from decision.decision_state import DecisionState, DecisionResult
from decision.emergency_safety import EmergencySafetyManager


class DecisionManager:
    """
    Central facade for Phase 13 decision-making hierarchy.
    """

    def __init__(self):
        self.emergency_safety = EmergencySafetyManager()
        self.last_decision = DecisionResult(state=DecisionState.NORMAL_DRIVING)

    def evaluate_decision(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        replanning_manager: Optional[ReplanningManager] = None,
        current_time: float = 0.0,
        goal_pos: Optional[Tuple[float, float]] = None,
    ) -> DecisionResult:
        """
        Evaluates safety decision priority ladder.
        Safety decisions strictly override efficiency goals.
        """
        converter = world_model.converter
        ego = world_model.ego_state
        def_start = converter.sim_to_world(5.0, 0.0)
        ego_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))

        if goal_pos is None:
            goal_pos = world_model.goal_position

        # Extract path & replanning metrics
        path_state: Optional[CurrentPathState] = None
        replanning_status: Optional[ReplanningStatus] = None
        min_clearance = 999.0
        peak_future_risk = 0.0
        path_valid = True

        if replanning_manager is not None:
            path_state = replanning_manager.current_state
            replanning_status = replanning_manager.status
            if path_state is not None:
                min_clearance = path_state.minimum_clearance
                peak_future_risk = path_state.current_peak_risk
                path_valid = path_state.path_valid
        elif hasattr(world_model, "planning_result") and world_model.planning_result is not None:
            res = world_model.planning_result
            path_valid = res.success
            if res.selected_corridor:
                min_clearance = res.selected_corridor.min_clearance
                peak_future_risk = res.selected_corridor.peak_risk

        # 1. Priority 1: Emergency Safety Hard Override (Imminent Collision, Hard Clearance Violation, Safety Hold)
        is_emergency, emergency_result = self.emergency_safety.check_emergency_stop(
            world_model=world_model,
            future_risk_field=future_risk_field,
            path_valid=path_valid,
            min_clearance=min_clearance,
            peak_future_risk=peak_future_risk,
            replanning_status=replanning_status,
            current_time=current_time,
        )
        if is_emergency and emergency_result is not None:
            self.last_decision = emergency_result
            return emergency_result

        # 2. Priority 1.5: Goal Reached Handling
        dist_to_goal = math.hypot(goal_pos[0] - ego_pos[0], goal_pos[1] - ego_pos[1])
        if dist_to_goal <= GOAL_TOLERANCE_DISTANCE:
            res = DecisionResult(
                state=DecisionState.GOAL_REACHED,
                target_speed_factor=0.0,
                explanation=f"Goal position reached (distance={dist_to_goal:.2f}m <= {GOAL_TOLERANCE_DISTANCE}m). Stopping safely.",
                priority_level=1,
                timestamp=current_time,
            )
            self.last_decision = res
            return res

        # 3. Priority 2: Replanning Requested State
        if replanning_status in (ReplanningStatus.REPLAN_REQUESTED, ReplanningStatus.PLANNING):
            res = DecisionResult(
                state=DecisionState.REPLAN,
                target_speed_factor=0.5,
                explanation="Active replanning in progress. Reducing target speed for safe trajectory transition.",
                priority_level=2,
                timestamp=current_time,
            )
            self.last_decision = res
            return res

        # Extract Uncertainty & Surface Hazard metrics
        high_uncertainty = False
        if hasattr(world_model, "uncertainty_grid") and world_model.uncertainty_grid is not None:
            if world_model.uncertainty_grid.get_max_uncertainty() >= HIGH_UNCERTAINTY_THRESHOLD:
                high_uncertainty = True

        max_surface_severity = 0.0
        if hasattr(world_model, "surface_model") and world_model.surface_model is not None:
            hazards = world_model.surface_model.get_hazards()
            for h in hazards:
                # Check proximity to ego
                if hasattr(h, "x") and hasattr(h, "y"):
                    d = math.hypot(h.x - ego_pos[0], h.y - ego_pos[1])
                    if d < 15.0:  # Surface hazard ahead within 15m
                        max_surface_severity = max(max_surface_severity, getattr(h, "severity", 0.5))

        # 4. Priority 3: Very High Future Risk / Severe Surface Hazard -> SLOW_DOWN
        if peak_future_risk >= HIGH_RISK_THRESHOLD or max_surface_severity >= HIGH_SURFACE_SEVERITY:
            res = DecisionResult(
                state=DecisionState.SLOW_DOWN,
                target_speed_factor=0.35,
                explanation=f"High risk detected (Risk={peak_future_risk:.2f}, Surface Severity={max_surface_severity:.2f}). Slowing down.",
                priority_level=3,
                timestamp=current_time,
            )
            self.last_decision = res
            return res

        # 5. Priority 3.5: Low Clearance -> SLOW_DOWN / CAUTION
        if min_clearance < LOW_CLEARANCE_THRESHOLD:
            res = DecisionResult(
                state=DecisionState.SLOW_DOWN,
                target_speed_factor=0.45,
                explanation=f"Low side clearance ({min_clearance:.2f}m < {LOW_CLEARANCE_THRESHOLD}m). Reducing speed.",
                priority_level=3,
                timestamp=current_time,
            )
            self.last_decision = res
            return res

        # 6. Priority 4: Moderate Risk / High Uncertainty / Moderate Surface Hazard -> CAUTION
        if (
            peak_future_risk >= MODERATE_RISK_THRESHOLD
            or high_uncertainty
            or max_surface_severity >= MODERATE_SURFACE_SEVERITY
        ):
            res = DecisionResult(
                state=DecisionState.CAUTION,
                target_speed_factor=0.65,
                explanation=f"Moderate risk or uncertainty ahead (Risk={peak_future_risk:.2f}, Uncertainty High={high_uncertainty}). Proceeding with caution.",
                priority_level=4,
                timestamp=current_time,
            )
            self.last_decision = res
            return res

        # 7. Priority 6: Normal Navigation
        res = DecisionResult(
            state=DecisionState.NORMAL_DRIVING,
            target_speed_factor=1.0,
            explanation="Path clear, risk low, clearance safe. Proceeding with nominal speed.",
            priority_level=6,
            timestamp=current_time,
        )
        self.last_decision = res
        return res
