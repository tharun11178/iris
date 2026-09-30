"""
IRIS Trigger Detector (Phase 12).
Evaluates current path state against hard and soft replanning triggers, prioritizing safety events
(PATH_BLOCKED, PREDICTED_COLLISION, LOW_CLEARANCE) and respecting cooldown limits for soft triggers.
"""

from typing import Tuple, Optional, Any
from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from replanning.config import (
    RISK_REPLAN_THRESHOLD,
    PEAK_RISK_INCREASE_THRESHOLD,
    MIN_CLEARANCE_THRESHOLD,
    HARD_CLEARANCE_THRESHOLD,
    UNCERTAINTY_REPLAN_THRESHOLD,
    PATH_SCORE_DEGRADATION_THRESHOLD,
    PATH_DEVIATION_THRESHOLD,
    MIN_REPLAN_INTERVAL,
    ENABLE_PERIODIC_REPLAN,
    PERIODIC_REPLAN_INTERVAL,
)
from replanning.path_state import CurrentPathState, ReplanReason, ReplanningDecision


class TriggerDetector:
    """
    Detects safety and performance triggers for adaptive replanning.
    """

    def __init__(
        self,
        risk_threshold: float = RISK_REPLAN_THRESHOLD,
        peak_increase_threshold: float = PEAK_RISK_INCREASE_THRESHOLD,
        min_clearance_threshold: float = MIN_CLEARANCE_THRESHOLD,
        hard_clearance_threshold: float = HARD_CLEARANCE_THRESHOLD,
        uncertainty_threshold: float = UNCERTAINTY_REPLAN_THRESHOLD,
        degradation_threshold: float = PATH_SCORE_DEGRADATION_THRESHOLD,
        deviation_threshold: float = PATH_DEVIATION_THRESHOLD,
        min_replan_interval: float = MIN_REPLAN_INTERVAL,
    ):
        self.risk_threshold = risk_threshold
        self.peak_increase_threshold = peak_increase_threshold
        self.min_clearance_threshold = min_clearance_threshold
        self.hard_clearance_threshold = hard_clearance_threshold
        self.uncertainty_threshold = uncertainty_threshold
        self.degradation_threshold = degradation_threshold
        self.deviation_threshold = deviation_threshold
        self.min_replan_interval = min_replan_interval

    def detect_trigger(
        self,
        path_state: CurrentPathState,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        current_time: float = 0.0,
    ) -> ReplanningDecision:
        """
        Evaluates current path state against hard and soft triggers in strict priority order.
        """
        time_since_replan = current_time - path_state.last_replan_time
        in_cooldown = time_since_replan < self.min_replan_interval

        # ------------------- HARD TRIGGERS (Override Cooldown) -------------------

        # 1. Hard Trigger 1: PATH_BLOCKED / Invalid Path
        if not path_state.path_valid or path_state.blocked_cell_count > 0:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=True,
                reason=ReplanReason.PATH_BLOCKED,
                severity=1.0,
                trigger_value=float(path_state.blocked_cell_count),
                threshold=0.0,
                timestamp=current_time,
                explanation=f"Active path is blocked by obstacle/non-traversable cell ({path_state.blocked_cell_count} cells blocked).",
            )

        # 2. Hard Trigger 2: PREDICTED_COLLISION (Extreme Peak Future Risk >= 0.85)
        if path_state.current_peak_risk >= 0.85:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=True,
                reason=ReplanReason.PREDICTED_COLLISION,
                severity=0.95,
                trigger_value=path_state.current_peak_risk,
                threshold=0.85,
                timestamp=current_time,
                explanation=f"Imminent predicted collision risk detected along path ({path_state.current_peak_risk:.2f} >= 0.85).",
            )

        # 3. Hard Trigger 3: Critical Low Clearance (< HARD_CLEARANCE_THRESHOLD)
        if path_state.minimum_clearance < self.hard_clearance_threshold:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=True,
                reason=ReplanReason.LOW_CLEARANCE,
                severity=0.90,
                trigger_value=path_state.minimum_clearance,
                threshold=self.hard_clearance_threshold,
                timestamp=current_time,
                explanation=f"Critical clearance violation: {path_state.minimum_clearance:.2f}m < {self.hard_clearance_threshold:.2f}m.",
            )

        # ------------------- SOFT TRIGGERS (Subject to Cooldown) -------------------

        # If soft trigger and within cooldown window, suppress soft replanning
        if in_cooldown:
            return ReplanningDecision(
                should_replan=False,
                is_hard_trigger=False,
                reason=ReplanReason.NO_REPLAN_REQUIRED,
                severity=0.0,
                trigger_value=0.0,
                threshold=0.0,
                timestamp=current_time,
                explanation=f"Replanning suppressed by cooldown interval ({time_since_replan:.2f}s < {self.min_replan_interval:.2f}s).",
            )

        # 4. Soft Trigger 4: HIGH_FUTURE_RISK / Peak Risk Increase
        peak_increase = path_state.current_peak_risk - path_state.original_peak_risk
        if path_state.current_peak_risk >= self.risk_threshold or peak_increase >= self.peak_increase_threshold:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=False,
                reason=ReplanReason.HIGH_FUTURE_RISK,
                severity=0.70,
                trigger_value=path_state.current_peak_risk,
                threshold=self.risk_threshold,
                timestamp=current_time,
                explanation=f"Predicted future risk exceeded threshold (Peak Risk={path_state.current_peak_risk:.2f}, Increase={peak_increase:.2f}).",
            )

        # 5. Soft Trigger 5: LOW_CLEARANCE (< MIN_CLEARANCE_THRESHOLD)
        if path_state.minimum_clearance < self.min_clearance_threshold:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=False,
                reason=ReplanReason.LOW_CLEARANCE,
                severity=0.60,
                trigger_value=path_state.minimum_clearance,
                threshold=self.min_clearance_threshold,
                timestamp=current_time,
                explanation=f"Clearance dropped below safe buffer threshold ({path_state.minimum_clearance:.2f}m < {self.min_clearance_threshold:.2f}m).",
            )

        # 6. Soft Trigger 6: HIGH_UNCERTAINTY
        uncertainty_val = 0.0
        if hasattr(world_model, "uncertainty_grid") and world_model.uncertainty_grid is not None:
            # Check maximum uncertainty along path
            u_grid = world_model.uncertainty_grid
            if path_state.path and path_state.path.world_points:
                u_vals = [
                    u_grid.get_uncertainty_at_world(px, py, world_model.converter)
                    for px, py in path_state.path.world_points[path_state.current_waypoint_index:]
                ]
                uncertainty_val = max(u_vals) if u_vals else 0.0

        if uncertainty_val >= self.uncertainty_threshold:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=False,
                reason=ReplanReason.HIGH_UNCERTAINTY,
                severity=0.50,
                trigger_value=uncertainty_val,
                threshold=self.uncertainty_threshold,
                timestamp=current_time,
                explanation=f"High prediction uncertainty along path ({uncertainty_val:.2f} >= {self.uncertainty_threshold:.2f}).",
            )

        # 7. Soft Trigger 7: PATH_SCORE_DEGRADED
        if path_state.original_score > 0.0:
            score_degradation = (path_state.current_score - path_state.original_score) / max(0.01, path_state.original_score)
            if score_degradation >= self.degradation_threshold:
                return ReplanningDecision(
                    should_replan=True,
                    is_hard_trigger=False,
                    reason=ReplanReason.PATH_SCORE_DEGRADED,
                    severity=0.40,
                    trigger_value=score_degradation,
                    threshold=self.degradation_threshold,
                    timestamp=current_time,
                    explanation=f"Path cost score degraded by {score_degradation*100.0:.1f}%.",
                )

        # 8. Soft Trigger 8: PATH_DEVIATION
        if path_state.path_deviation >= self.deviation_threshold:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=False,
                reason=ReplanReason.PATH_DEVIATION,
                severity=0.35,
                trigger_value=path_state.path_deviation,
                threshold=self.deviation_threshold,
                timestamp=current_time,
                explanation=f"Ego vehicle path deviation exceeded limit ({path_state.path_deviation:.2f}m >= {self.deviation_threshold:.2f}m).",
            )

        # 9. Soft Trigger 9: PERIODIC_REFRESH
        if ENABLE_PERIODIC_REPLAN and time_since_replan >= PERIODIC_REPLAN_INTERVAL:
            return ReplanningDecision(
                should_replan=True,
                is_hard_trigger=False,
                reason=ReplanReason.PERIODIC_REFRESH,
                severity=0.10,
                trigger_value=time_since_replan,
                threshold=PERIODIC_REPLAN_INTERVAL,
                timestamp=current_time,
                explanation=f"Periodic safety refresh timer expired ({time_since_replan:.1f}s >= {PERIODIC_REPLAN_INTERVAL:.1f}s).",
            )

        # Default: No Replan Required
        return ReplanningDecision(
            should_replan=False,
            is_hard_trigger=False,
            reason=ReplanReason.NO_REPLAN_REQUIRED,
            severity=0.0,
            trigger_value=0.0,
            threshold=0.0,
            timestamp=current_time,
            explanation="Current path remains valid and optimal.",
        )
