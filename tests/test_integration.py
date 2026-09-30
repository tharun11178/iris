"""
IRIS Full 16-Phase System Integration Test Suite.
Verifies phase-by-phase connectivity (P1 through P16) and full closed-loop step execution.
"""

import os
import shutil
import unittest
import numpy as np

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
from evaluation.scenario_metrics import ScenarioMetricsTracker
from integration.matlab.matlab_adapter import MatlabAdapter
from integration.simulink.simulink_adapter import SimulinkAdapter
from integration.roadrunner.roadrunner_actor_mapping import RoadRunnerActorMapper
from core.iris_system import IRISSystem


class TestFull16PhaseIntegration(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_integration_output"
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_phase_1_to_phase_2(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        self.assertIsNotNone(wm.grid)
        self.assertGreater(len(wm.grid.cells), 0)

    def test_phase_2_to_phase_3_astar(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        planner = Planner(allow_diagonal=False)
        start = wm.converter.sim_to_world(env.ego_vehicle.x, env.ego_vehicle.y)
        goal = wm.goal_position
        path = planner.plan(start, goal, wm)
        self.assertIsNotNone(path)

    def test_phase_5_to_phase_4_risk(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        re = RiskEngine()
        re.update(wm)
        self.assertIsNotNone(re.risk_grid)
        self.assertGreaterEqual(re.risk_grid.get_max_risk(), 0.0)

    def test_phase_6_to_phase_7_tracking(self):
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        tm = TrackManager()
        dets = pm.process(env)
        tracks = tm.update(dets, timestamp=env.sim_time)
        self.assertIsInstance(tracks, list)

    def test_phase_7_to_phase_8_prediction(self):
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        tm = TrackManager()
        pred_m = PredictionManager()
        wm = WorldModel()
        wm.update_from_environment(env)

        dets = pm.process(env)
        tracks = tm.update(dets, timestamp=env.sim_time)
        prediction_set = pred_m.predict(tracks, timestamp=env.sim_time, road_evaluator=wm.is_drivable_at_world)
        self.assertIsNotNone(prediction_set)

    def test_phase_8_to_phase_9_uncertainty(self):
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        tm = TrackManager()
        pred_m = PredictionManager()
        unc_m = UncertaintyManager()
        wm = WorldModel()
        wm.update_from_environment(env)

        dets = pm.process(env)
        tracks = tm.update(dets, timestamp=env.sim_time)
        prediction_set = pred_m.predict(tracks, timestamp=env.sim_time, road_evaluator=wm.is_drivable_at_world)
        uncertainty_set = unc_m.evaluate_uncertainty(tracks, prediction_set, current_time=env.sim_time)
        self.assertIsNotNone(uncertainty_set)

    def test_phase_9_to_phase_10_future_risk(self):
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        tm = TrackManager()
        pred_m = PredictionManager()
        unc_m = UncertaintyManager()
        fre = FutureRiskEngine()
        wm = WorldModel()

        dets = pm.process(env)
        tracks = tm.update(dets, timestamp=env.sim_time)
        prediction_set = pred_m.predict(tracks, timestamp=env.sim_time, road_evaluator=wm.is_drivable_at_world)
        uncertainty_set = unc_m.evaluate_uncertainty(tracks, prediction_set, current_time=env.sim_time)

        wm.update_from_environment(
            env, perception_manager=pm, track_manager=tm,
            prediction_manager=pred_m, prediction_set=prediction_set,
            uncertainty_manager=unc_m, uncertainty_set=uncertainty_set,
            future_risk_engine=fre
        )
        fre.update(wm, prediction_set, uncertainty_set, env.sim_time)
        self.assertIsNotNone(wm.future_risk_field)

    def test_phase_10_to_phase_11_safe_space(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        ssp = SafeSpacePlanner()
        start = wm.converter.sim_to_world(env.ego_vehicle.x, env.ego_vehicle.y)
        goal = wm.goal_position
        res = ssp.plan(wm, wm.future_risk_field, start, goal)
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.selected_path)

    def test_phase_11_to_phase_12_replanning(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        ssp = SafeSpacePlanner()
        rm = ReplanningManager(planner=ssp)
        start = wm.converter.sim_to_world(env.ego_vehicle.x, env.ego_vehicle.y)
        goal = wm.goal_position

        rm.update(env.sim_time, start, goal, wm, wm.future_risk_field)
        active_path = rm.get_active_path()
        self.assertIsNotNone(active_path)

    def test_phase_12_to_phase_13_decision_control(self):
        env = SimulationEnvironment()
        wm = WorldModel()
        wm.update_from_environment(env)
        ssp = SafeSpacePlanner()
        rm = ReplanningManager(planner=ssp)
        vc = VehicleController()
        goal = wm.goal_position

        cmd = vc.compute_control(wm, wm.future_risk_field, rm, dt=0.05, current_time=env.sim_time, goal_pos=goal)
        self.assertIsNotNone(cmd)
        self.assertIsNotNone(cmd.decision_result)

    def test_phase_14_scenarios(self):
        sm = ScenarioManager(seed=42)
        sc = sm.load_scenario("SUDDEN_CATTLE_CROSSING", seed=42)
        self.assertIsNotNone(sc)

    def test_phase_15_metrics(self):
        env = SimulationEnvironment()
        tracker = ScenarioMetricsTracker(scenario_id="TEST", seed=42)
        tracker.update_step(env, dt=0.05)
        m = tracker.finalize()
        self.assertIsNotNone(m)

    def test_phase_16_integrations(self):
        env = SimulationEnvironment()
        ma = MatlabAdapter()
        sa = SimulinkAdapter()
        rr = RoadRunnerActorMapper()

        payload = ma.serialize_iris_state(env)
        self.assertIn("ego_vehicle", payload)

        bus = sa.export_simulink_bus_signals(env)
        self.assertIn("EgoVehicleBus", bus)

        act = rr.map_roadrunner_asset("Vehicle.Rickshaw.Auto")
        self.assertEqual(act.name, "AUTO_RICKSHAW")

    def test_full_system_closed_loop_execution(self):
        """Full Closed-Loop System Integration Test."""
        config = {
            "scenario": "SUDDEN_CATTLE_CROSSING",
            "planner": "iris",
            "mode": "simulation",
            "seed": 42,
            "duration": 1.0,
            "headless": True
        }
        system = IRISSystem(config=config)
        system.initialize()

        self.assertTrue(system.running)
        self.assertEqual(system.step_count, 0)

        # Step closed loop for 5 steps
        for _ in range(5):
            system.step()

        self.assertGreater(system.step_count, 0)
        self.assertGreater(system.env.sim_time, 0.0)

        system.shutdown()


if __name__ == "__main__":
    unittest.main()
