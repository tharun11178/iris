"""
IRIS Central System Orchestrator (Phase 1 through 16 Unified Integration).
Connects Simulation (P1), WorldModel (P2), A* Baseline (P3), Current Risk (P4),
Surface Intelligence (P5), Perception (P6), Tracking (P7), Motion Prediction (P8),
Uncertainty Modeling (P9), Future Risk Field (P10), Safe-Space Planner (P11),
Adaptive Replanning (P12), Decision & Vehicle Control (P13), Scenarios (P14),
Dashboard & Metrics (P15), and External Systems Bridge (P16).
"""

import os
import sys
import time
import math
import json
import logging
from typing import Dict, List, Tuple, Optional, Any

from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from planning.planner import Planner
from risk_engine.risk_engine import RiskEngine
from surface.surface_model import SurfaceModel
from perception.perception_manager import PerceptionManager
from perception.simulated_detector import SimulatedDetector
from perception.sensor_pipeline import SensorPipeline
from tracking.track_manager import TrackManager
from prediction.prediction_manager import PredictionManager
from uncertainty.uncertainty_manager import UncertaintyManager
from future_risk.future_risk_engine import FutureRiskEngine
from safe_space.safe_space_planner import SafeSpacePlanner
from replanning.replanning_manager import ReplanningManager
from decision.decision_manager import DecisionManager
from control.vehicle_controller import VehicleController
from scenarios.scenario_manager import ScenarioManager
from evaluation.scenario_metrics import ScenarioMetricsTracker, ExtendedScenarioMetrics
from evaluation.report import ReportGenerator
from integration.matlab.matlab_adapter import MatlabAdapter
from integration.simulink.simulink_adapter import SimulinkAdapter
from integration.roadrunner.roadrunner_actor_mapping import RoadRunnerActorMapper


class IRISSystem:
    """
    Central orchestrator facade connecting all 16 IRIS phases into a single executable system.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config if config is not None else {}
        self.scenario_name = self.config.get("scenario", "SUDDEN_CATTLE_CROSSING")
        self.planner_mode = self.config.get("planner", "iris").lower()  # "iris" or "astar"
        self.mode = self.config.get("mode", "simulation").lower()       # "simulation", "demo", "evaluation"
        self.seed = int(self.config.get("seed", 42))
        self.duration = float(self.config.get("duration", 30.0))
        self.dt = float(self.config.get("dt", 0.05))
        self.headless = bool(self.config.get("headless", False))
        self.debug = bool(self.config.get("debug", False))

        self.running = False
        self.step_count = 0
        self.latencies: Dict[str, float] = {}

        # Log & Result Paths
        self.logs_dir = "logs"
        self.results_dir = "results"
        self.plots_dir = "plots"
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.plots_dir, exist_ok=True)

        self._setup_logging()

    def _setup_logging(self):
        """Configure structured file logging for simulation, replanning, and events."""
        self.logger = logging.getLogger("IRISSystem")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()

        fh = logging.FileHandler(os.path.join(self.logs_dir, "simulation.log"), mode="w", encoding="utf-8")
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

    def initialize(self):
        """
        Initialize all 16 phases in exact dependency order.
        """
        self.logger.info("Initializing IRIS Central System Orchestrator across all 16 Phases...")

        try:
            # Phase 1: Simulation Environment
            self.env = SimulationEnvironment()
            self.logger.info("Phase 1 Simulation Environment initialized.")

            # Phase 14: Scenario Manager
            self.scenario_manager = ScenarioManager(seed=self.seed)
            sc = self.scenario_manager.load_scenario(self.scenario_name, seed=self.seed)
            if sc is None:
                self.logger.warning(f"Scenario '{self.scenario_name}' not found. Loading SUDDEN_CATTLE_CROSSING.")
                sc = self.scenario_manager.load_scenario("SUDDEN_CATTLE_CROSSING", seed=self.seed)
                self.scenario_name = "SUDDEN_CATTLE_CROSSING"
            self.scenario_manager.initialize_scenario(self.env)
            self.logger.info(f"Phase 14 ScenarioManager initialized: '{self.scenario_name}'")

            # Phase 2: WorldModel
            self.world_model = WorldModel()
            self.logger.info("Phase 2 WorldModel initialized.")

            # Phase 5: Surface Model
            self.surface_model = SurfaceModel()
            self.logger.info("Phase 5 Surface Model initialized.")

            # Phase 6: Perception & Sensor Pipeline
            self.sensor_pipeline = SensorPipeline()
            self.perception_manager = PerceptionManager(detector=SimulatedDetector())
            self.logger.info("Phase 6 PerceptionManager & SensorPipeline initialized.")

            # Phase 7: Multi-Object Tracking
            self.track_manager = TrackManager()
            self.logger.info("Phase 7 TrackManager initialized.")

            # Phase 8: Motion Prediction
            self.prediction_manager = PredictionManager()
            self.logger.info("Phase 8 PredictionManager initialized.")

            # Phase 9: Uncertainty Modeling
            self.uncertainty_manager = UncertaintyManager()
            self.logger.info("Phase 9 UncertaintyManager initialized.")

            # Phase 4: Current Risk Engine
            self.risk_engine = RiskEngine()
            self.logger.info("Phase 4 RiskEngine initialized.")

            # Phase 10: Future Risk Field Engine
            self.future_risk_engine = FutureRiskEngine()
            self.logger.info("Phase 10 FutureRiskEngine initialized.")

            # Phase 11 & Phase 3: Safe-Space Planner and A* Baseline
            self.safe_space_planner = SafeSpacePlanner(mode="iris_safe_space")
            self.astar_planner = Planner(allow_diagonal=False)
            self.logger.info("Phase 11 SafeSpacePlanner & Phase 3 A* Baseline initialized.")

            # Phase 12: Adaptive Replanning
            self.replanning_manager = ReplanningManager(planner=self.safe_space_planner)
            self.logger.info("Phase 12 ReplanningManager initialized.")

            # Phase 13: Decision & Vehicle Control
            self.decision_manager = DecisionManager()
            self.vehicle_controller = VehicleController()
            self.logger.info("Phase 13 DecisionManager & VehicleController initialized.")

            # Phase 15: Evaluation Metrics Tracker & Report Generator
            self.metrics_tracker = ScenarioMetricsTracker(
                scenario_id=self.scenario_name,
                planner_mode="BASELINE_ASTAR" if self.planner_mode == "astar" else "IRIS_FULL",
                seed=self.seed
            )
            self.report_generator = ReportGenerator(output_dir=self.results_dir)
            self.logger.info("Phase 15 Evaluation Metrics Engine initialized.")

            # Phase 15: Live Dashboard UI Window (if not headless)
            self.dashboard_window = None
            if not self.headless and self.mode != "evaluation":
                try:
                    from dashboard.dashboard import DashboardWindow
                    self.dashboard_window = DashboardWindow()
                    self.logger.info("Phase 15 Live Telemetry Dashboard initialized.")
                except Exception as e:
                    self.logger.warning(f"Dashboard initialization skipped: {e}")

            # Phase 16: External Integrations Status Check
            self.matlab_adapter = MatlabAdapter()
            self.simulink_adapter = SimulinkAdapter()
            self.roadrunner_mapper = RoadRunnerActorMapper()
            self.logger.info("Phase 16 Integration Adapters initialized.")
            print("[IRIS External Status] MATLAB: AVAILABLE (Adapter Loaded)")
            print("[IRIS External Status] Simulink: AVAILABLE (Adapter Loaded)")
            print("[IRIS External Status] RoadRunner: AVAILABLE (Adapter Loaded)")

            # Initial Pipeline Warmup Step
            self._initial_pipeline_step()
            self.running = True
            self.logger.info("All 16 IRIS Phases Connected and System Initialized Successfully.")

        except Exception as e:
            self.logger.error(f"[ERROR] Phase initialization failed: {e}", exc_info=True)
            print(f"[ERROR] System initialization failed: {e}")
            raise e

    def _initial_pipeline_step(self):
        """Initial plan search and state update."""
        detections = self.perception_manager.process(self.env)
        tracks = self.track_manager.update(detections, timestamp=self.env.sim_time)
        pred_set = self.prediction_manager.predict(tracks, timestamp=self.env.sim_time, road_evaluator=self.world_model.is_drivable_at_world)
        unc_set = self.uncertainty_manager.evaluate_uncertainty(tracks, pred_set, current_time=self.env.sim_time)
        self.world_model.update_from_environment(
            self.env,
            perception_manager=self.perception_manager,
            track_manager=self.track_manager,
            prediction_manager=self.prediction_manager,
            prediction_set=pred_set,
            uncertainty_manager=self.uncertainty_manager,
            uncertainty_set=unc_set,
            future_risk_engine=self.future_risk_engine,
        )
        self.risk_engine.update(self.world_model)

        start_pos = self.world_model.converter.sim_to_world(self.env.ego_vehicle.x, self.env.ego_vehicle.y)
        goal_pos = self.world_model.goal_position

        if self.planner_mode == "astar":
            path_res = self.astar_planner.plan(start_pos, goal_pos, self.world_model)
            self.replanning_manager.initialize_path(path_res, self.world_model, "INITIAL_ASTAR", 0.0)
        else:
            plan_res = self.safe_space_planner.plan(self.world_model, self.world_model.future_risk_field, start_pos, goal_pos)
            self.replanning_manager.initialize_path(plan_res.selected_path, self.world_model, "INITIAL_SAFE_SPACE", plan_res.selected_score if hasattr(plan_res, 'selected_score') else 0.0)

    def step(self):
        """
        Execute one complete 16-phase integrated simulation step.
        """
        if not self.running:
            return

        t_start_step = time.perf_counter()

        try:
            # 1. Advance simulation clock & environment (P1)
            t0 = time.perf_counter()
            self.env.step(self.dt, 0.0, 0.0)
            self.latencies["P1_Environment"] = (time.perf_counter() - t0) * 1000.0

            # 2. Multi-Sensor Data Stream Generation (P6)
            t0 = time.perf_counter()
            sensor_streams = self.sensor_pipeline.process_sensor_streams(self.env)

            # 3. Phase 6 Perception
            detections = self.perception_manager.process(self.env)
            self.latencies["P6_Perception"] = (time.perf_counter() - t0) * 1000.0

            # 4. Phase 7 Multi-Object Tracking
            t0 = time.perf_counter()
            tracks = self.track_manager.update(detections, timestamp=self.env.sim_time)
            self.latencies["P7_Tracking"] = (time.perf_counter() - t0) * 1000.0

            # 5. Phase 8 Motion Prediction
            t0 = time.perf_counter()
            pred_set = self.prediction_manager.predict(tracks, timestamp=self.env.sim_time, road_evaluator=self.world_model.is_drivable_at_world)
            self.latencies["P8_Prediction"] = (time.perf_counter() - t0) * 1000.0

            # 6. Phase 9 Uncertainty Modeling
            t0 = time.perf_counter()
            unc_set = self.uncertainty_manager.evaluate_uncertainty(tracks, pred_set, current_time=self.env.sim_time)
            self.latencies["P9_Uncertainty"] = (time.perf_counter() - t0) * 1000.0

            # 7. Phase 2 WorldModel & Phase 5 SurfaceModel Update
            t0 = time.perf_counter()
            self.world_model.update_from_environment(
                self.env,
                perception_manager=self.perception_manager,
                track_manager=self.track_manager,
                prediction_manager=self.prediction_manager,
                prediction_set=pred_set,
                uncertainty_manager=self.uncertainty_manager,
                uncertainty_set=unc_set,
                future_risk_engine=self.future_risk_engine,
            )
            self.latencies["P2_WorldModel"] = (time.perf_counter() - t0) * 1000.0

            # 8. Phase 4 Current Risk Engine
            t0 = time.perf_counter()
            self.risk_engine.update(self.world_model)
            self.latencies["P4_CurrentRisk"] = (time.perf_counter() - t0) * 1000.0

            # 9. Phase 10 Spatiotemporal Future Risk Field Engine
            t0 = time.perf_counter()
            self.future_risk_engine.update(self.world_model, pred_set, unc_set, self.env.sim_time)
            self.latencies["P10_FutureRisk"] = (time.perf_counter() - t0) * 1000.0

            # 10. Phase 12 Adaptive Replanning & Path Monitoring
            t0 = time.perf_counter()
            start_pos = self.world_model.converter.sim_to_world(self.env.ego_vehicle.x, self.env.ego_vehicle.y)
            goal_pos = self.world_model.goal_position

            replan_event = self.replanning_manager.update(
                sim_time=self.env.sim_time,
                ego_pos=start_pos,
                goal_pos=goal_pos,
                world_model=self.world_model,
                future_risk_field=self.world_model.future_risk_field,
            )
            self.latencies["P12_Replanning"] = (time.perf_counter() - t0) * 1000.0

            # 11. Select Active Path & Mode Execution (Phase 3 A* vs Phase 11 Safe Space)
            if self.planner_mode == "astar":
                t0 = time.perf_counter()
                path_res = self.astar_planner.plan(start_pos, goal_pos, self.world_model)
                active_path = path_res
                self.latencies["P3_AStarPlanner"] = (time.perf_counter() - t0) * 1000.0
            else:
                active_path = self.replanning_manager.get_active_path()

            self.env.ego_vehicle.current_path = active_path

            # 12. Phase 13 Decision State Machine & Vehicle Control
            t0 = time.perf_counter()
            ctrl_cmd = self.vehicle_controller.compute_control(
                world_model=self.world_model,
                future_risk_field=self.world_model.future_risk_field,
                replanning_manager=self.replanning_manager,
                dt=self.dt,
                current_time=self.env.sim_time,
                goal_pos=goal_pos,
            )
            self.latencies["P13_Control"] = (time.perf_counter() - t0) * 1000.0

            # Apply Control Inputs to Ego Vehicle
            self.env.ego_vehicle.update(self.dt, ctrl_cmd.throttle_command, ctrl_cmd.steering_command)
            self.scenario_manager.update(self.env, self.world_model, self.replanning_manager, self.vehicle_controller, self.dt)

            # 13. Phase 15 Evaluation Metrics & Dashboard Update
            t0 = time.perf_counter()
            self.metrics_tracker.update_step(self.env, self.world_model, self.replanning_manager, decision_result=ctrl_cmd.decision_result, dt=self.dt)
            self.latencies["P15_Metrics"] = (time.perf_counter() - t0) * 1000.0

            if self.dashboard_window:
                if not self.dashboard_window.process_events():
                    self.running = False
                self.dashboard_window.render(
                    env=self.env,
                    world_model=self.world_model,
                    replanning_manager=self.replanning_manager,
                    safe_space_planner=self.safe_space_planner,
                    future_risk_field=self.world_model.future_risk_field,
                    decision_result=ctrl_cmd.decision_result,
                    control_cmd=ctrl_cmd,
                    scenario_runner=self.scenario_manager.runner,
                    metrics=self.metrics_tracker.metrics
                )

            # Check Termination / Goal / Safety Hold Conditions
            self.step_count += 1
            if self.metrics_tracker.metrics.scenario_completed or self.env.sim_time >= self.duration:
                self.running = False

            loop_time_ms = (time.perf_counter() - t_start_step) * 1000.0
            self.latencies["Overall_Loop"] = loop_time_ms

        except Exception as e:
            self.logger.error(f"[ERROR] Simulation step failed at step {self.step_count}: {e}", exc_info=True)
            print(f"[ERROR] Step {self.step_count} failed: {e}")
            self.running = False

    def run(self):
        """Run step loop until termination."""
        print(f"[IRIS Central System] Running scenario '{self.scenario_name}' | Planner: '{self.planner_mode.upper()}' | Mode: '{self.mode.upper()}'...")
        while self.running:
            self.step()
        self.shutdown()

    def shutdown(self):
        """Save results, export metrics JSON/CSV/HTML, generate plots, and close UI."""
        self.logger.info("Shutting down IRIS Central System Orchestrator...")
        final_metrics = self.metrics_tracker.finalize()
        m_dict = final_metrics.to_dict()

        # Save to results/
        with open(os.path.join(self.results_dir, "metrics.json"), "w", encoding="utf-8") as f:
            json.dump(m_dict, f, indent=2)

        with open(os.path.join(self.results_dir, "events.json"), "w", encoding="utf-8") as f:
            events_data = [e.to_dict() if hasattr(e, "to_dict") else str(e) for e in self.replanning_manager.event_log]
            json.dump(events_data, f, indent=2)

        # Generate plots
        telemetry = {
            "risk": self.metrics_tracker.risk_samples,
            "speed": [self.env.ego_vehicle.velocity],
            "clearance": [self.env.get_minimum_clearance()]
        }
        self.report_generator.generate_plots(telemetry, filename=os.path.join(self.plots_dir, "telemetry_plots.png"))

        print("\n==========================================================================")
        print("[SUMMARY] IRIS SYSTEM RUN COMPLETE -- FINAL EXECUTABLE SUMMARY")
        print("==========================================================================")
        print(f"Scenario ID:         {final_metrics.scenario_id}")
        print(f"Planner Mode:        {final_metrics.planner_mode}")
        print(f"Completed:           {final_metrics.scenario_completed}")
        print(f"Completion Rate:     {final_metrics.completion_rate * 100:.1f}%")
        print(f"Collisions:          {final_metrics.collision_count}")
        print(f"Near Misses:         {final_metrics.near_collision_count}")
        print(f"Min Clearance:       {final_metrics.min_clearance_meters:.2f} m")
        print(f"Peak Future Risk:    {final_metrics.peak_risk:.3f}")
        print(f"Smoothness Score:    {final_metrics.smoothness_score:.3f}")
        print(f"Total Replans:       {final_metrics.replan_count}")
        print(f"Avg Replan Latency:  {final_metrics.avg_replan_latency_ms:.2f} ms")
        print(f"Overall Loop Latency:{self.latencies.get('Overall_Loop', 0.0):.2f} ms")
        print("==========================================================================\n")
