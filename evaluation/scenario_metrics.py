"""
IRIS Scenario Metrics Aggregator (Combined Phase 15).
Tracks, records, and aggregates quantitative evaluation metrics over full scenario execution runs.
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from evaluation.metrics import MetricsCalculator, CollisionRecord, SmoothnessMetrics


@dataclass
class ExtendedScenarioMetrics:
    """Complete quantitative evaluation metrics container for IRIS scenario execution."""
    scenario_id: str = "UNKNOWN"
    planner_mode: str = "IRIS_FULL"
    configuration_name: str = "FULL"
    seed: int = 42
    scenario_completed: bool = False
    completion_rate: float = 0.0
    collision_occurred: bool = False
    collision_count: int = 0
    collision_timestamps: List[float] = field(default_factory=list)
    collision_records: List[Dict[str, Any]] = field(default_factory=list)
    near_collision_count: int = 0
    min_clearance_meters: float = 999.0
    min_ttc_seconds: float = 999.0
    replan_count: int = 0
    unnecessary_replans: int = 0
    avg_replan_latency_ms: float = 0.0
    total_path_length: float = 0.0
    total_travel_time: float = 0.0
    smoothness_score: float = 1.0
    total_heading_change: float = 0.0
    mean_curvature: float = 0.0
    max_curvature: float = 0.0
    peak_risk: float = 0.0
    average_risk: float = 0.0
    max_uncertainty: float = 0.0
    emergency_stops: int = 0
    safety_holds: int = 0
    expected_events_fulfilled: int = 0
    total_expected_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScenarioMetricsTracker:
    """
    Online tracker aggregating step-by-step evaluation metrics during scenario simulation.
    """

    def __init__(self, scenario_id: str, planner_mode: str = "IRIS_FULL",
                 config_name: str = "FULL", seed: int = 42,
                 near_collision_threshold: float = 1.2):
        self.metrics = ExtendedScenarioMetrics(
            scenario_id=scenario_id,
            planner_mode=planner_mode,
            configuration_name=config_name,
            seed=seed
        )
        self.calculator = MetricsCalculator(near_collision_threshold=near_collision_threshold)
        self.risk_samples: List[float] = []
        self.ego_path_history: List[Tuple[float, float]] = []
        self.last_replan_risk: float = 0.0
        self.last_replan_time: float = -1.0

    def update_step(self, env: Any, world_model: Optional[Any] = None,
                    replanning_manager: Optional[Any] = None,
                    decision_result: Optional[Any] = None,
                    dt: float = 0.05):
        """Update metrics for a single simulation timestep."""
        sim_time = getattr(env, "sim_time", 0.0)
        ego = env.ego_vehicle

        self.ego_path_history.append((ego.x, ego.y))
        self.metrics.total_travel_time = max(self.metrics.total_travel_time + dt, sim_time)
        self.metrics.total_path_length = ego.path_length

        # Check goal clearance
        dx_goal = env.road.length - ego.x
        if abs(dx_goal) < 2.0:
            self.metrics.scenario_completed = True
            self.metrics.completion_rate = 1.0
        else:
            self.metrics.completion_rate = min(1.0, max(0.0, ego.x / max(1.0, env.road.length)))

        # 1. Clearance & Min Distance
        clearance = env.get_minimum_clearance()
        if clearance < self.metrics.min_clearance_meters:
            self.metrics.min_clearance_meters = clearance

        if clearance < self.calculator.near_collision_threshold:
            self.metrics.near_collision_count += 1

        ego_heading = getattr(ego, "heading", 0.0)
        ego_vx = ego.velocity * math.cos(ego_heading)
        ego_vy = ego.velocity * math.sin(ego_heading)

        # 2. Collisions & TTC
        for actor in env.traffic_actors:
            act_heading = getattr(actor, "heading", 0.0)
            act_vx = getattr(actor, "vx", actor.velocity * math.cos(act_heading))
            act_vy = getattr(actor, "vy", actor.velocity * math.sin(act_heading))

            if self.calculator.is_collision(ego.x, ego.y, ego.length, ego.width,
                                            actor.x, actor.y, actor.length, actor.width):
                # Avoid multi-counting same collision continuously within 0.5s window
                if not self.metrics.collision_timestamps or (sim_time - self.metrics.collision_timestamps[-1]) > 0.5:
                    self.metrics.collision_occurred = True
                    self.metrics.collision_count += 1
                    self.metrics.collision_timestamps.append(sim_time)
                    rel_v = math.hypot(ego_vx - act_vx, ego_vy - act_vy)
                    rec = CollisionRecord(
                        timestamp=sim_time,
                        actor_id=actor.actor_id,
                        actor_type=str(actor.actor_type.name if hasattr(actor.actor_type, 'name') else actor.actor_type),
                        ego_x=ego.x, ego_y=ego.y,
                        actor_x=actor.x, actor_y=actor.y,
                        relative_velocity=rel_v
                    )
                    self.metrics.collision_records.append(asdict(rec))

            ttc = self.calculator.calculate_ttc(
                ego.x, ego.y, ego_vx, ego_vy,
                actor.x, actor.y, act_vx, act_vy
            )
            if ttc < self.metrics.min_ttc_seconds:
                self.metrics.min_ttc_seconds = ttc

        # 3. Risk Tracking
        step_risk = 0.0
        if replanning_manager and hasattr(replanning_manager, "current_state") and replanning_manager.current_state:
            step_risk = replanning_manager.current_state.current_peak_risk

        self.risk_samples.append(step_risk)
        self.metrics.peak_risk = max(self.metrics.peak_risk, step_risk)
        if self.risk_samples:
            self.metrics.average_risk = float(np.mean(self.risk_samples))

        # 4. Uncertainty Tracking
        if world_model and hasattr(world_model, "uncertainty_grid") and world_model.uncertainty_grid:
            unc = world_model.uncertainty_grid.get_max_uncertainty()
            self.metrics.max_uncertainty = max(self.metrics.max_uncertainty, unc)

        # 5. Replanning Metrics
        if replanning_manager:
            rm = replanning_manager.metrics
            old_replan_cnt = self.metrics.replan_count
            self.metrics.replan_count = rm.total_replans
            self.metrics.avg_replan_latency_ms = rm.avg_latency_ms

            if self.metrics.replan_count > old_replan_cnt:
                # Check if replan was unnecessary (risk was low and path was clear)
                if step_risk < 0.20 and clearance > 2.0:
                    self.metrics.unnecessary_replans += 1

        # 6. Decision & Emergency Actions
        if decision_result:
            st = str(decision_result.state.name if hasattr(decision_result.state, 'name') else decision_result.state)
            if st == "STOP":
                self.metrics.emergency_stops += 1
            elif st == "SAFETY_HOLD":
                self.metrics.safety_holds += 1

        # 7. Smoothness Update
        sm = self.calculator.calculate_path_smoothness(self.ego_path_history)
        self.metrics.smoothness_score = sm.smoothness_score
        self.metrics.total_heading_change = sm.total_heading_change
        self.metrics.mean_curvature = sm.mean_curvature
        self.metrics.max_curvature = sm.max_curvature

    def finalize(self) -> ExtendedScenarioMetrics:
        """Finalize metrics calculations at end of run."""
        if self.metrics.min_clearance_meters == 999.0:
            self.metrics.min_clearance_meters = 0.0
        if self.metrics.min_ttc_seconds == 999.0:
            self.metrics.min_ttc_seconds = 0.0
        return self.metrics
