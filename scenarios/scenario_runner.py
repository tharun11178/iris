"""
IRIS Scenario Runner & Metrics Evaluator (Combined Phase 14).
Executes reproducible scenario runs, processes dynamic event triggers, collects evaluation
metrics matrix, checks expected event fulfillment, and records benchmark test results.
"""

import math
import time
import json
import random
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from simulation.entities import ActorType
from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from replanning.replanning_manager import ReplanningManager
from scenarios.scenario_definition import ScenarioDefinition, ScenarioMetrics, ExpectedEvent
from scenarios.scenario_events import ScenarioEventEngine
from scenarios.scenario_loader import ScenarioRegistry


class ScenarioRunner:
    """
    Orchestrates execution, event dispatching, metrics tracking, and evaluation for IRIS scenarios.
    """

    def __init__(self, registry: Optional[ScenarioRegistry] = None):
        self.registry = registry if registry is not None else ScenarioRegistry()
        self.event_engine = ScenarioEventEngine()
        self.current_scenario: Optional[ScenarioDefinition] = None
        self.metrics = ScenarioMetrics()
        self.executed_events: List[Any] = []

        # Tracking accumulators
        self.latencies: List[float] = []
        self.min_clearance_recorded: float = 999.0
        self.max_risk_recorded: float = 0.0
        self.max_uncertainty_recorded: float = 0.0
        self.smoothness_accum: float = 0.0
        self.last_steering: float = 0.0

    def load_scenario(self, scenario_id: str, seed: int = 42) -> Optional[ScenarioDefinition]:
        """Loads scenario definition by ID and initializes random seed."""
        sc = self.registry.get_scenario(scenario_id, seed)
        if sc is not None:
            self.current_scenario = sc
            self.reset_metrics()
            # Set deterministic random seed
            random.seed(seed)
            np.random.seed(seed)
        return sc

    def reset_metrics(self):
        """Resets tracking metrics."""
        if self.current_scenario:
            self.metrics = ScenarioMetrics(
                scenario_id=self.current_scenario.scenario_id,
                scenario_name=self.current_scenario.name,
            )
        else:
            self.metrics = ScenarioMetrics()

        self.executed_events.clear()
        self.latencies.clear()
        self.min_clearance_recorded = 999.0
        self.max_risk_recorded = 0.0
        self.max_uncertainty_recorded = 0.0
        self.smoothness_accum = 0.0
        self.last_steering = 0.0

    def initialize_environment(self, env: SimulationEnvironment) -> bool:
        """Populates SimulationEnvironment with actors and surface hazards defined in scenario."""
        if self.current_scenario is None:
            return False

        sc = self.current_scenario
        env.reset()
        env.ego_vehicle.x, env.ego_vehicle.y = sc.start_pos

        # Clear default environment entities
        env.traffic_actors.clear()
        env.surface_hazards.clear()

        # Instantiate static scenario actors
        for sa in sc.actors:
            actor = sa.actor_type
            from simulation.entities import TrafficActor
            a = TrafficActor(sa.actor_id, sa.actor_type, sa.x, sa.y, sa.heading, sa.velocity, sa.behavior)
            env.traffic_actors.append(a)

        # Instantiate static scenario hazards
        for sh in sc.hazards:
            from simulation.entities import SurfaceHazard
            h = SurfaceHazard(sh.hazard_id, sh.hazard_type, sh.x, sh.y, sh.length, sh.width, sh.severity, sh.uncertainty)
            env.surface_hazards.append(h)

        return True

    def step(
        self,
        env: SimulationEnvironment,
        world_model: WorldModel,
        replanning_manager: Optional[ReplanningManager] = None,
        vehicle_controller: Optional[Any] = None,
        dt: float = 0.05,
    ) -> ScenarioMetrics:
        """
        Executes single scenario update step, dispatches events, updates metrics, and checks expected events.
        """
        if self.current_scenario is None:
            return self.metrics

        sc = self.current_scenario
        sim_time = env.sim_time

        # 1. Process Dynamic Event System Triggers
        if sc.events:
            executed = self.event_engine.process_events(env, sc.events, sim_time, dt)
            self.executed_events.extend(executed)

        # 2. Update Metrics Accumulators
        ego = env.ego_vehicle
        ego_pos = (ego.x, ego.y)

        # Distance to goal check
        dist_goal = math.hypot(sc.goal_pos[0] - ego_pos[0], sc.goal_pos[1] - ego_pos[1])
        if dist_goal <= 2.0 or ego.goal_reached:
            self.metrics.completed = True

        # Minimum Clearance & Near Collisions
        clearance = 999.0
        if replanning_manager and replanning_manager.current_state:
            clearance = replanning_manager.current_state.minimum_clearance
        elif hasattr(world_model, "planning_result") and world_model.planning_result and world_model.planning_result.selected_corridor:
            clearance = world_model.planning_result.selected_corridor.min_clearance

        self.min_clearance_recorded = min(self.min_clearance_recorded, clearance)
        self.metrics.min_clearance = self.min_clearance_recorded

        if clearance < 1.0:
            self.metrics.near_collision_count += 1

        # Check hard actor collision
        for actor in env.traffic_actors:
            d_act = math.hypot(actor.x - ego.x, actor.y - ego.y)
            if d_act < (ego.length + actor.length) / 2.5:
                self.metrics.collision_occurred = True

        # Future Risk Peak
        peak_risk = 0.0
        if replanning_manager and replanning_manager.current_state:
            peak_risk = replanning_manager.current_state.current_peak_risk
        self.max_risk_recorded = max(self.max_risk_recorded, peak_risk)
        self.metrics.max_future_risk = self.max_risk_recorded

        # Uncertainty Peak
        if hasattr(world_model, "uncertainty_grid") and world_model.uncertainty_grid:
            unc = world_model.uncertainty_grid.get_max_uncertainty()
            self.max_uncertainty_recorded = max(self.max_uncertainty_recorded, unc)
            self.metrics.max_uncertainty = self.max_uncertainty_recorded

        # Replanning Metrics
        if replanning_manager:
            m = replanning_manager.metrics
            self.metrics.replan_count = m.total_replans
            self.metrics.avg_replan_latency_ms = m.avg_latency_ms

        # Smoothness (Steering Rate Change)
        curr_steer = ego.steering_angle
        d_steer = abs(curr_steer - self.last_steering)
        self.smoothness_accum += d_steer
        self.last_steering = curr_steer

        self.metrics.total_path_length = ego.path_length
        self.metrics.total_travel_time = max(ego.travel_time, sim_time)
        self.metrics.smoothness_score = max(0.0, 1.0 - (self.smoothness_accum / max(1.0, sim_time * 10.0)))

        # 3. Check Expected Events Fulfillment
        self._evaluate_expected_events(env, replanning_manager, sim_time)

        return self.metrics

    def _evaluate_expected_events(self, env: SimulationEnvironment, replanning_manager: Optional[Any], sim_time: float):
        """Checks expected scenario evaluation checkpoints."""
        if self.current_scenario is None:
            return

        for ee in self.current_scenario.expected_events:
            if ee.triggered:
                continue

            cond = ee.trigger_condition.lower()
            if cond == "cattle_crossing":
                for a in env.traffic_actors:
                    if a.actor_type == ActorType.CATTLE and abs(a.x - env.ego_vehicle.x) < 15.0:
                        ee.triggered = True
                        ee.timestamp_triggered = sim_time
            elif cond == "replanning":
                if replanning_manager and replanning_manager.metrics.total_replans > 0:
                    ee.triggered = True
                    ee.timestamp_triggered = sim_time
            elif cond == "risk_increase":
                if self.max_risk_recorded > 0.5:
                    ee.triggered = True
                    ee.timestamp_triggered = sim_time
            elif cond == "slowdown":
                if env.ego_vehicle.velocity < 4.0:
                    ee.triggered = True
                    ee.timestamp_triggered = sim_time
            elif cond == "stop":
                if env.ego_vehicle.velocity < 0.1:
                    ee.triggered = True
                    ee.timestamp_triggered = sim_time

    def to_dict(self) -> Dict[str, Any]:
        """Serializes scenario run metrics."""
        m = self.metrics
        return {
            "scenario_id": m.scenario_id,
            "scenario_name": m.scenario_name,
            "completed": m.completed,
            "collision_occurred": m.collision_occurred,
            "near_collision_count": m.near_collision_count,
            "min_clearance_meters": round(m.min_clearance, 2),
            "replan_count": m.replan_count,
            "avg_replan_latency_ms": round(m.avg_replan_latency_ms, 2),
            "total_path_length_meters": round(m.total_path_length, 2),
            "total_travel_time_seconds": round(m.total_travel_time, 2),
            "smoothness_score": round(m.smoothness_score, 3),
            "max_future_risk": round(m.max_future_risk, 2),
            "max_uncertainty": round(m.max_uncertainty, 2),
            "executed_events_count": len(self.executed_events),
        }
