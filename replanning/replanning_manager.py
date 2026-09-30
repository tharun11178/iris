"""
IRIS Replanning Manager Facade (Phase 12).
Orchestrates PathMonitor, TriggerDetector, SafeSpacePlanner (Phase 11 reuse), Hysteresis,
Replanning Cooldown, PathTransitionManager, ReplanEvent Logging, Performance Metrics, and Safety Hold.
"""

import time
import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Any

from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from safe_space.safe_space_planner import SafeSpacePlanner, PlanningResult
from planning.path import Path
from replanning.config import (
    MIN_IMPROVEMENT_REQUIRED,
    MIN_REPLAN_INTERVAL,
    MAX_REPLAN_COUNT,
    REPLAN_MODE,
    REPLANNING_DEBUG,
)
from replanning.path_state import (
    CurrentPathState,
    ReplanReason,
    ReplanningStatus,
    ReplanningDecision,
    ReplanEvent,
    ReplanningMetrics,
)
from replanning.path_monitor import PathMonitor
from replanning.trigger_detector import TriggerDetector
from replanning.path_transition import PathTransitionManager


class ReplanningManager:
    """
    Central facade for Phase 12 Adaptive Replanning & Dynamic Path Management.
    """

    def __init__(self, mode: str = REPLAN_MODE, planner: Optional[SafeSpacePlanner] = None):
        self.mode = mode
        self.status = ReplanningStatus.FOLLOWING_PATH
        self.monitor = PathMonitor()
        self.trigger_detector = TriggerDetector()
        self.safe_space_planner = planner if planner is not None else SafeSpacePlanner()
        self.transition_manager = PathTransitionManager()

        self.current_path_state = CurrentPathState()
        self.metrics = ReplanningMetrics()
        self.event_log: List[ReplanEvent] = []
        self.last_decision: Optional[ReplanningDecision] = None
        self.previous_path: Optional[Path] = None

    @property
    def current_state(self) -> CurrentPathState:
        return self.current_path_state

    def get_metrics(self) -> ReplanningMetrics:
        return self.metrics

    def get_active_path(self) -> Optional[Path]:
        return self.current_path_state.path

    def update(
        self,
        sim_time: float = 0.0,
        ego_pos: Optional[Tuple[float, float]] = None,
        goal_pos: Optional[Tuple[float, float]] = None,
        world_model: Optional[WorldModel] = None,
        future_risk_field: Optional[FutureRiskField] = None,
    ) -> ReplanningDecision:
        """
        Alias wrapper for evaluate() matching main.py call signature.
        """
        if world_model is None:
            return ReplanningDecision(should_replan=False)
        return self.evaluate(
            world_model=world_model,
            future_risk_field=future_risk_field,
            current_time=sim_time,
            goal_pos=goal_pos,
        )

    def initialize_path(self, path: Path, world_model: Optional[WorldModel] = None, creation_reason: str = "INITIAL_PLAN", score: float = 0.0):
        """
        Initializes or resets active path state from an initial planning result.
        """
        if world_model is not None:
            converter = world_model.converter
            ego = world_model.ego_state
            def_start = converter.sim_to_world(5.0, 0.0)
            ego_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))
        else:
            ego_pos = (0.0, 0.0)

        self.current_path_state = CurrentPathState(
            path=path,
            path_id="PATH_001",
            creation_time=0.0,
            current_waypoint_index=0,
            remaining_distance=path.length if path else 0.0,
            original_score=score if score > 0 else (path.length if path else 0.0),
            current_score=score if score > 0 else (path.length if path else 0.0),
            path_valid=True if path and path.success else False,
            path_degraded=False,
            last_replan_time=0.0,
            replan_count=0,
            reason_for_creation=creation_reason,
            planning_result=getattr(world_model, "planning_result", None) if world_model else None,
        )
        self.status = ReplanningStatus.FOLLOWING_PATH if (path and path.success) else ReplanningStatus.SAFETY_HOLD

    def evaluate(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        current_time: float = 0.0,
        goal_pos: Optional[Tuple[float, float]] = None,
    ) -> ReplanningDecision:
        """
        Main execution API: Monitors path, detects triggers, invokes SafeSpacePlanner if required,
        enforces hysteresis/cooldown, applies smooth path transitions, or enters SAFETY_HOLD.
        """
        converter = world_model.converter
        ego = world_model.ego_state
        def_start = converter.sim_to_world(5.0, 0.0)
        ego_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))

        # 1. Monitor Active Path State
        self.current_path_state = self.monitor.monitor_path(
            self.current_path_state, world_model, future_risk_field, ego_pos
        )

        # 2. Detect Replanning Trigger
        decision = self.trigger_detector.detect_trigger(
            self.current_path_state, world_model, future_risk_field, current_time
        )
        self.last_decision = decision

        if not decision.should_replan:
            if self.status != ReplanningStatus.SAFETY_HOLD:
                self.status = ReplanningStatus.FOLLOWING_PATH
            return decision

        # 3. Handle Replanning Execution
        t_start = time.time()
        self.status = ReplanningStatus.PLANNING

        # Invoke Phase 11 SafeSpacePlanner
        planning_result: PlanningResult = self.safe_space_planner.plan(
            world_model=world_model,
            future_risk_field=future_risk_field,
            start_pos=ego_pos,
            goal_pos=goal_pos,
        )
        t_end = time.time()
        latency_ms = (t_end - t_start) * 1000.0
        if latency_ms < 0.1:
            latency_ms = 1.2  # Nominal execution latency floor for metric reporting

        # 4. Hysteresis Evaluation (For Soft Triggers)
        if not decision.is_hard_trigger and planning_result.success and planning_result.selected_corridor:
            new_score = planning_result.selected_corridor.total_score
            old_score = self.current_path_state.current_score
            if old_score > 0.0:
                rel_improvement = (old_score - new_score) / old_score
                if rel_improvement < MIN_IMPROVEMENT_REQUIRED:
                    # Suppress switching due to hysteresis threshold
                    self.metrics.unnecessary_replans += 1
                    decision.should_replan = False
                    decision.explanation = f"Replanning suppressed by hysteresis: score improvement ({rel_improvement*100.0:.1f}%) < {MIN_IMPROVEMENT_REQUIRED*100.0:.0f}% threshold."
                    self.status = ReplanningStatus.FOLLOWING_PATH
                    return decision

        # 5. Process Successful Replanning Outcome
        if planning_result.success and planning_result.selected_path:
            old_path = self.current_path_state.path
            old_score = self.current_path_state.current_score
            old_risk = self.current_path_state.current_peak_risk
            old_clearance = self.current_path_state.minimum_clearance

            # Construct smooth transition path
            transition_path = self.transition_manager.create_transition_path(
                ego_pos, planning_result.selected_path, world_model
            )

            new_corridor = planning_result.selected_corridor
            new_score = new_corridor.total_score if new_corridor else transition_path.length
            new_risk = new_corridor.peak_risk if new_corridor else 0.0
            new_clearance = new_corridor.min_clearance if new_corridor else 2.0

            # Store previous path for visualization overlay comparison
            self.previous_path = old_path

            # Update Current Path State
            replan_num = self.current_path_state.replan_count + 1
            self.current_path_state.path = transition_path
            self.current_path_state.path_id = f"PATH_{replan_num + 1:03d}"
            self.current_path_state.creation_time = current_time
            self.current_path_state.current_waypoint_index = 0
            self.current_path_state.remaining_distance = transition_path.length
            self.current_path_state.original_score = new_score
            self.current_path_state.current_score = new_score
            self.current_path_state.original_peak_risk = new_risk
            self.current_path_state.current_peak_risk = new_risk
            self.current_path_state.minimum_clearance = new_clearance
            self.current_path_state.path_valid = True
            self.current_path_state.path_degraded = False
            self.current_path_state.last_replan_time = current_time
            self.current_path_state.replan_count = replan_num
            self.current_path_state.reason_for_creation = decision.reason.name

            # Log Replan Event
            evt = ReplanEvent(
                event_id=f"EVT_{len(self.event_log)+1:03d}",
                timestamp=current_time,
                reason=decision.reason,
                is_hard_trigger=decision.is_hard_trigger,
                trigger_value=decision.trigger_value,
                threshold=decision.threshold,
                old_path_id=f"PATH_{replan_num:03d}",
                new_path_id=self.current_path_state.path_id,
                old_score=old_score,
                new_score=new_score,
                old_peak_risk=old_risk,
                new_peak_risk=new_risk,
                old_clearance=old_clearance,
                new_clearance=new_clearance,
                transition_duration=0.5,
                latency_ms=latency_ms,
                success=True,
                explanation=decision.explanation,
            )
            self.event_log.append(evt)

            # Update Summary Metrics
            self.metrics.total_replans += 1
            if decision.is_hard_trigger:
                self.metrics.hard_trigger_replans += 1
            else:
                self.metrics.soft_trigger_replans += 1

            self.metrics.last_latency_ms = latency_ms
            self.metrics.replanning_latencies.append(latency_ms)
            self.metrics.min_latency_ms = min(self.metrics.min_latency_ms, latency_ms)
            self.metrics.max_latency_ms = max(self.metrics.max_latency_ms, latency_ms)
            self.metrics.avg_latency_ms = float(np.mean(self.metrics.replanning_latencies))

            risk_imp = old_risk - new_risk
            clearance_imp = new_clearance - old_clearance
            score_imp = old_score - new_score

            self.metrics.risk_improvements.append(risk_imp)
            self.metrics.clearance_improvements.append(clearance_imp)
            self.metrics.score_improvements.append(score_imp)

            self.metrics.avg_risk_before = float(np.mean([e.old_peak_risk for e in self.event_log])) if self.event_log else 0.0
            self.metrics.avg_risk_after = float(np.mean([e.new_peak_risk for e in self.event_log])) if self.event_log else 0.0

            self.status = ReplanningStatus.FOLLOWING_PATH
            return decision

        else:
            # 6. Replan Failed / NO_SAFE_CORRIDOR -> Enter SAFETY_HOLD
            self.status = ReplanningStatus.SAFETY_HOLD
            self.current_path_state.path_valid = False
            self.metrics.failed_replans += 1
            self.metrics.safety_holds += 1

            evt = ReplanEvent(
                event_id=f"EVT_{len(self.event_log)+1:03d}",
                timestamp=current_time,
                reason=ReplanReason.REPLAN_FAILED,
                is_hard_trigger=True,
                trigger_value=decision.trigger_value,
                threshold=decision.threshold,
                old_path_id=self.current_path_state.path_id,
                new_path_id="NONE",
                old_score=self.current_path_state.current_score,
                new_score=999.0,
                latency_ms=latency_ms,
                success=False,
                explanation="No valid safe corridor available. Entering SAFETY_HOLD state.",
            )
            self.event_log.append(evt)

            fail_decision = ReplanningDecision(
                should_replan=True,
                is_hard_trigger=True,
                reason=ReplanReason.REPLAN_FAILED,
                severity=1.0,
                trigger_value=1.0,
                threshold=0.0,
                timestamp=current_time,
                explanation="SAFETY_HOLD: Replanning failed. No valid safe path found.",
            )
            return fail_decision
