"""
IRIS Comprehensive Full-Pipeline Automated Test Suite.
Verifies the complete closed-loop 16-phase sequential data flow:
Environment -> WorldModel -> Perception -> Tracking -> Prediction -> Uncertainty ->
CurrentRisk -> FutureRiskField -> SafeSpace -> Replanning -> Decision -> Control -> VehicleMovement.
"""

import unittest
import numpy as np
import os
import shutil

from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from perception.perception_manager import PerceptionManager
from tracking.track_manager import TrackManager
from prediction.prediction_manager import PredictionManager
from uncertainty.uncertainty_manager import UncertaintyManager
from risk_engine.risk_engine import RiskEngine
from future_risk.future_risk_engine import FutureRiskEngine
from safe_space.safe_space_planner import SafeSpacePlanner
from replanning.replanning_manager import ReplanningManager
from control.vehicle_controller import VehicleController
from core.iris_system import IRISSystem


class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_pipeline_output"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_complete_16_phase_data_flow(self):
        """
        Step-by-step sequential verification of real data passing from Module N to Module N+1.
        """
        # 1. Environment Simulation (Phase 1)
        env = SimulationEnvironment()
        self.assertIsNotNone(env.ego_vehicle)
        self.assertGreater(len(env.traffic_actors), 0)
        self.assertGreater(len(env.surface_hazards), 0)

        # 2. Perception Pipeline (Phase 6)
        perception_mgr = PerceptionManager()
        detections = perception_mgr.process(env)
        self.assertIsInstance(detections, list)

        # 3. Multi-Object MOT Tracking (Phase 7)
        track_mgr = TrackManager()
        tracks = track_mgr.update(detections, timestamp=env.sim_time)
        self.assertIsInstance(tracks, list)

        # 4. Motion Prediction (Phase 8)
        prediction_mgr = PredictionManager()
        prediction_set = prediction_mgr.predict(tracks, timestamp=env.sim_time)
        self.assertIsNotNone(prediction_set)

        # 5. Uncertainty Modeling (Phase 9)
        uncertainty_mgr = UncertaintyManager()
        uncertainty_set = uncertainty_mgr.evaluate_uncertainty(tracks, prediction_set, current_time=env.sim_time)
        self.assertIsNotNone(uncertainty_set)

        # 6. Spatial World Model (Phase 2)
        world_model = WorldModel()
        world_model.update_from_environment(
            env,
            perception_manager=perception_mgr,
            track_manager=track_mgr,
            prediction_manager=prediction_mgr,
            prediction_set=prediction_set,
            uncertainty_manager=uncertainty_mgr,
            uncertainty_set=uncertainty_set,
        )
        self.assertIsNotNone(world_model.grid)
        self.assertGreater(len(world_model.grid.cells), 0)

        # 7. Instantaneous Risk Engine (Phase 4)
        risk_engine = RiskEngine()
        risk_engine.update(world_model)
        self.assertIsNotNone(risk_engine.risk_grid)
        self.assertGreaterEqual(risk_engine.risk_grid.get_max_risk(), 0.0)

        # 8. Spatiotemporal Future Risk Field (Phase 10)
        future_risk_engine = FutureRiskEngine()
        future_risk_field = future_risk_engine.update(world_model, prediction_set, uncertainty_set, env.sim_time)
        self.assertIsNotNone(future_risk_field)
        self.assertGreater(len(future_risk_field.risk_grids), 0)

        # 9. Safe-Space / Negative-Space Planner (Phase 11 & 12)
        safe_space_planner = SafeSpacePlanner()
        start_pos = world_model.converter.sim_to_world(env.ego_vehicle.x, env.ego_vehicle.y)
        goal_pos = world_model.goal_position
        plan_result = safe_space_planner.plan(world_model, future_risk_field, start_pos, goal_pos)
        self.assertIsNotNone(plan_result)
        self.assertIsNotNone(plan_result.selected_path)

        # 10. Adaptive Replanning (Phase 12)
        replanning_mgr = ReplanningManager()
        replanning_mgr.initialize_path(plan_result.selected_path, world_model, "INIT", 0.0)
        replan_event = replanning_mgr.update(
            sim_time=env.sim_time,
            ego_pos=start_pos,
            goal_pos=goal_pos,
            world_model=world_model,
            future_risk_field=future_risk_field,
        )
        active_path = replanning_mgr.get_active_path()
        self.assertIsNotNone(active_path)

        # 11. Decision State Machine (Phase 13) & Vehicle Controller (Phase 14)
        controller = VehicleController()
        control_cmd = controller.compute_control(
            world_model=world_model,
            future_risk_field=future_risk_field,
            replanning_manager=replanning_mgr,
            dt=0.05,
            current_time=env.sim_time,
            goal_pos=goal_pos,
        )
        self.assertIsNotNone(control_cmd)
        self.assertIsNotNone(control_cmd.decision_result)
        self.assertIsInstance(control_cmd.steering_command, (float, int, np.floating))
        self.assertIsInstance(control_cmd.throttle_command, (float, int, np.floating))

        # 12. Physical Movement Application
        old_x = env.ego_vehicle.x
        env.ego_vehicle.update(0.05, control_cmd.throttle_command, control_cmd.steering_command)
        self.assertNotEqual(env.ego_vehicle.x, old_x)

    def test_full_closed_loop_iris_system(self):
        """
        Tests multi-step closed-loop execution using central IRISSystem orchestrator facade.
        """
        system = IRISSystem({
            "scenario": "SUDDEN_CATTLE_CROSSING",
            "planner": "iris",
            "mode": "simulation",
            "seed": 42,
            "headless": True,
            "duration": 1.0,
        })
        system.initialize()
        self.assertTrue(system.running)

        for _ in range(10):
            system.step()

        self.assertGreater(system.step_count, 0)
        self.assertGreater(system.env.sim_time, 0.0)
        self.assertIsNotNone(system.env.ego_vehicle.current_path)
        system.shutdown()


if __name__ == "__main__":
    unittest.main()
