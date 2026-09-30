"""
IRIS Motion Prediction Unit and Integration Test Suite (Phase 8).
Tests all 20 specified prediction unit test scenarios and end-to-end integration test using standard unittest.
"""

import math
import unittest
from perception.object_classes import ObjectClass
from perception.detected_object import DetectedObject
from tracking.track import Track, TrackState
from tracking.track_manager import TrackManager
from prediction.trajectory import (
    PredictedTrajectory,
    PredictionHypothesis,
    PredictionSet,
    FutureOccupancy,
)
from prediction.behavior_model import get_behavior_profile, classify_motion_pattern, BehaviorCategory
from prediction.motion_predictor import MotionPredictor
from prediction.prediction_manager import PredictionManager
from evaluation.prediction_metrics import PredictionEvaluator
from simulation.environment import SimulationEnvironment
from perception.perception_manager import PerceptionManager
from perception.simulated_detector import SimulatedDetector
from world.world_model import WorldModel
from risk_engine.risk_engine import RiskEngine


class TestPredictionModule(unittest.TestCase):
    def setUp(self):
        self.predictor = MotionPredictor(horizon=3.0, time_step=0.2)
        self.manager = PredictionManager(predictor=self.predictor)
        self.evaluator = PredictionEvaluator()

    # 1. Stationary object
    def test_1_stationary_object(self):
        track = Track(
            track_id="TRACK_001",
            object_type=ObjectClass.CAR,
            current_position=(10.0, 5.0),
            velocity=(0.0, 0.0),
            speed=0.0,
            confidence=0.9,
        )
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        self.assertEqual(len(traj.predicted_positions), 15)  # 3.0s / 0.2s = 15 steps
        for px, py in traj.predicted_positions:
            self.assertAlmostEqual(px, 10.0)
            self.assertAlmostEqual(py, 5.0)

    # 2. Constant velocity object
    def test_2_constant_velocity_object(self):
        track = Track(
            track_id="TRACK_002",
            object_type=ObjectClass.CAR,
            current_position=(0.0, 0.0),
            velocity=(10.0, 0.0),  # 10 m/s along +X
            speed=10.0,
            confidence=0.9,
        )
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        self.assertEqual(traj.predicted_positions[0], (2.0, 0.0))    # t=0.2s -> x=2.0
        self.assertEqual(traj.predicted_positions[4], (10.0, 0.0))   # t=1.0s -> x=10.0
        self.assertEqual(traj.predicted_positions[-1], (30.0, 0.0))  # t=3.0s -> x=30.0

    # 3. Moving car
    def test_3_moving_car(self):
        track = Track("TRACK_003", ObjectClass.CAR, (5.0, 2.0), velocity=(5.0, 0.0), speed=5.0)
        prediction_set = self.manager.predict([track], timestamp=0.0)
        self.assertEqual(len(prediction_set.trajectories), 1)
        self.assertEqual(prediction_set.trajectories[0].model_name, "constant_velocity")
        self.assertEqual(prediction_set.trajectories[0].envelope_margins, (0.5, 0.5))

    # 4. Moving pedestrian
    def test_4_moving_pedestrian(self):
        track = Track("TRACK_004", ObjectClass.PEDESTRIAN, (10.0, 1.0), velocity=(1.5, 0.0), speed=1.5)
        prediction_set = self.manager.predict([track], timestamp=0.0)
        self.assertEqual(len(prediction_set.trajectories), 1)
        self.assertEqual(prediction_set.trajectories[0].envelope_margins[0], 1.2)  # Pedestrian margin

    # 5. Moving motorcycle
    def test_5_moving_motorcycle(self):
        track = Track("TRACK_005", ObjectClass.MOTORCYCLE, (15.0, -1.0), velocity=(8.0, 0.0), speed=8.0)
        prediction_set = self.manager.predict([track], timestamp=0.0)
        self.assertEqual(len(prediction_set.trajectories), 1)
        self.assertEqual(prediction_set.trajectories[0].envelope_margins[0], 1.0)  # Motorcycle margin

    # 6. Moving cattle (Multi-hypothesis prediction)
    def test_6_moving_cattle(self):
        track = Track("TRACK_006", ObjectClass.CATTLE, (20.0, 0.0), velocity=(1.2, 0.0), speed=1.2)
        prediction_set = self.manager.predict([track], timestamp=0.0)
        self.assertEqual(len(prediction_set.trajectories), 1)
        # Cattle generates 3 hypotheses (Forward, Turn Left, Turn Right)
        self.assertEqual(len(prediction_set.hypotheses), 3)
        h_types = {h.behavior_type for h in prediction_set.hypotheses}
        self.assertEqual(h_types, {"FORWARD", "TURN_LEFT", "TURN_RIGHT"})

    # 7. Heading calculation
    def test_7_heading_calculation(self):
        track = Track("TRACK_007", ObjectClass.CAR, (0.0, 0.0), velocity=(0.0, 10.0), speed=10.0)
        heading = self.predictor.estimate_heading(track)
        self.assertAlmostEqual(heading, math.pi / 2.0, delta=0.01)

    # 8. Speed calculation
    def test_8_speed_calculation(self):
        track = Track("TRACK_008", ObjectClass.CAR, (0.0, 0.0), velocity=(3.0, 4.0), speed=5.0)
        self.assertAlmostEqual(track.speed, 5.0)

    # 9. Prediction horizon
    def test_9_prediction_horizon(self):
        track = Track("TRACK_009", ObjectClass.CAR, (0.0, 0.0), velocity=(5.0, 0.0), speed=5.0)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        self.assertEqual(traj.prediction_horizon, 3.0)

    # 10. Time-step generation
    def test_10_time_step_generation(self):
        offsets, timestamps = self.predictor.generate_time_steps(10.0)
        self.assertEqual(len(offsets), 15)
        self.assertAlmostEqual(offsets[0], 0.2)
        self.assertAlmostEqual(offsets[-1], 3.0)
        self.assertAlmostEqual(timestamps[0], 10.2)
        self.assertAlmostEqual(timestamps[-1], 13.0)

    # 11. Constant velocity prediction equation
    def test_11_constant_velocity_equation(self):
        track = Track("TRACK_011", ObjectClass.CAR, (10.0, 20.0), velocity=(2.0, -1.0), speed=2.236)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        # t=1.0s => x = 10 + 2*1 = 12.0, y = 20 - 1*1 = 19.0
        self.assertAlmostEqual(traj.predicted_positions[4][0], 12.0)
        self.assertAlmostEqual(traj.predicted_positions[4][1], 19.0)

    # 12. Constant acceleration prediction equation
    def test_12_constant_acceleration_equation(self):
        track = Track(
            "TRACK_012",
            ObjectClass.CAR,
            (0.0, 0.0),
            velocity=(10.0, 0.0),
            speed=10.0,
            acceleration=(2.0, 0.0),
        )
        traj = self.predictor.predict_constant_acceleration(track, start_timestamp=0.0)
        # t=1.0s => x = 0 + 10*1 + 0.5*2*(1^2) = 11.0
        self.assertAlmostEqual(traj.predicted_positions[4][0], 11.0)

    # 13. Prediction envelope
    def test_13_prediction_envelope(self):
        profile_ped = get_behavior_profile(ObjectClass.PEDESTRIAN)
        profile_car = get_behavior_profile(ObjectClass.CAR)
        self.assertEqual(profile_ped.lateral_margin, 1.2)
        self.assertEqual(profile_car.lateral_margin, 0.5)

    # 14. Multi-hypothesis prediction
    def test_14_multi_hypothesis_prediction(self):
        track = Track("TRACK_014", ObjectClass.CATTLE, (0.0, 0.0), velocity=(2.0, 0.0), speed=2.0)
        hypotheses = self.predictor.predict_multi_hypothesis(track, start_timestamp=0.0)
        self.assertEqual(len(hypotheses), 3)

        # H1 Forward should have y ~ 0.0
        # H2 Turn Left should have positive y
        # H3 Turn Right should have negative y
        h1_last_y = hypotheses[0].trajectory.predicted_positions[-1][1]
        h2_last_y = hypotheses[1].trajectory.predicted_positions[-1][1]
        h3_last_y = hypotheses[2].trajectory.predicted_positions[-1][1]

        self.assertAlmostEqual(h1_last_y, 0.0, delta=0.1)
        self.assertGreater(h2_last_y, 0.5)
        self.assertLess(h3_last_y, -0.5)

    # 15. Stopped object handling
    def test_15_stopped_object_handling(self):
        track = Track("TRACK_015", ObjectClass.CAR, (10.0, 5.0), velocity=(0.1, 0.0), speed=0.1)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        # Speed < 0.3 m/s => stays at (10.0, 5.0)
        self.assertEqual(traj.predicted_positions[-1], (10.0, 5.0))

    # 16. Invalid velocity handling
    def test_16_invalid_velocity_handling(self):
        track = Track("TRACK_016", ObjectClass.CAR, (10.0, 5.0), velocity=(0.0, 0.0), speed=0.0)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        self.assertEqual(len(traj.predicted_positions), 15)

    # 17. Missing history handling
    def test_17_missing_history_handling(self):
        track = Track("TRACK_017", ObjectClass.CAR, (10.0, 5.0), velocity=(5.0, 0.0), speed=5.0)
        track.history = []
        motion_cat = classify_motion_pattern(track)
        self.assertEqual(motion_cat, BehaviorCategory.FORWARD)

    # 18. Low-confidence track prediction
    def test_18_low_confidence_track_prediction(self):
        track = Track("TRACK_018", ObjectClass.CAR, (10.0, 5.0), velocity=(5.0, 0.0), speed=5.0, confidence=0.4)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)
        self.assertLess(traj.confidence, 0.4)

    # 19. Road-boundary prediction plausibility
    def test_19_road_boundary_plausibility(self):
        def dummy_road_eval(x, y):
            return -6.0 <= y <= 6.0

        track = Track("TRACK_019", ObjectClass.CAR, (0.0, 5.5), velocity=(0.0, 2.0), speed=2.0)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0, road_evaluator=dummy_road_eval)
        self.assertIn(False, traj.road_plausibility)  # Moves out of road bound y > 6.0

    # 20. Future grid occupancy
    def test_20_future_grid_occupancy(self):
        class DummyConverter:
            def world_to_grid(self, x, y):
                return int(y + 10), int(x)

        track = Track("TRACK_020", ObjectClass.CAR, (0.0, 0.0), velocity=(5.0, 0.0), speed=5.0)
        prediction_set = self.manager.predict([track], timestamp=0.0)
        future_occupancies = self.manager.convert_to_future_occupancy(
            prediction_set, DummyConverter(), grid_cols=100, grid_rows=100, grid_res=0.5
        )
        self.assertEqual(len(future_occupancies), 1)
        self.assertGreater(len(future_occupancies[0].grid_cells), 0)

    # 21. Evaluation Metrics Test
    def test_21_prediction_evaluator(self):
        track = Track("TRACK_021", ObjectClass.CAR, (0.0, 0.0), velocity=(10.0, 0.0), speed=10.0)
        traj = self.predictor.predict_constant_velocity(track, start_timestamp=0.0)

        # Ground truth moves slightly slower: 9 m/s
        gt_future = [(1.8, 0.0), (3.6, 0.0), (5.4, 0.0), (7.2, 0.0), (9.0, 0.0)]
        res = self.evaluator.evaluate_trajectory(traj, gt_future)
        self.assertGreater(res["ade"], 0.0)
        self.assertAlmostEqual(res["fde"], 1.0, delta=0.1)  # At t=1.0s, pred x=10.0, gt x=9.0 => fde=1.0m

    # 22. End-to-End Integration Test
    def test_22_phase8_full_integration(self):
        """
        Integration test:
        Simulation -> Perception -> TrackManager -> PredictionManager -> FutureOccupancy -> WorldModel
        """
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        track_mgr = TrackManager()
        pred_mgr = PredictionManager()
        wm = WorldModel()
        risk_eng = RiskEngine()

        # Step 1: Perception
        dets = pm.process(env)
        # Step 2: Tracking
        tracks = track_mgr.update(dets, timestamp=env.sim_time)
        # Step 3: Motion Prediction
        pred_set = pred_mgr.predict(tracks, timestamp=env.sim_time)
        # Step 4: WorldModel Update
        wm.update_from_environment(
            env,
            perception_manager=pm,
            track_manager=track_mgr,
            prediction_manager=pred_mgr,
            prediction_set=pred_set,
        )
        # Step 5: RiskEngine Update
        risk_eng.update(wm)

        self.assertIsNotNone(wm.prediction_set)
        self.assertGreaterEqual(len(wm.future_occupancies), len(tracks))
        self.assertIsNotNone(risk_eng.risk_grid)


if __name__ == "__main__":
    unittest.main()
