"""
Unit and Integration Tests for IRIS Phase 9: Uncertainty Modeling
===================================================================
Tests perception confidence uncertainty, velocity variance, heading circular wrap-around,
behavior multi-hypothesis disagreement, prediction horizon growth, geometric uncertainty ellipses,
spatial uncertainty grid rasterization, and system integration.
"""

import unittest
import math
import numpy as np

from tracking.track import Track, TrackState
from perception.simulated_detector import DetectedObject
from simulation.entities import ActorType as ObjectType
from prediction.trajectory import (
    PredictedTrajectory,
    PredictionHypothesis as MotionHypothesis,
    PredictionSet,
)
from world.world_model import WorldModel
from world.coordinate_system import CoordinateConverter
from simulation.environment import SimulationEnvironment

from uncertainty.config import UncertaintyConfig
from uncertainty.uncertainty_model import (
    UncertaintyState,
    UncertaintyEllipse,
    UncertaintyRegion,
    UncertaintyGrid,
    UncertaintySet,
)
from uncertainty.position_uncertainty import PositionUncertaintyEstimator
from uncertainty.velocity_uncertainty import VelocityUncertaintyEstimator
from uncertainty.heading_uncertainty import HeadingUncertaintyEstimator
from uncertainty.behavior_uncertainty import BehaviorUncertaintyEstimator
from uncertainty.prediction_uncertainty import PredictionUncertaintyEstimator
from uncertainty.uncertainty_manager import UncertaintyManager


class TestUncertaintyModeling(unittest.TestCase):
    def setUp(self):
        self.config = UncertaintyConfig()
        self.pos_est = PositionUncertaintyEstimator(self.config)
        self.vel_est = VelocityUncertaintyEstimator(self.config)
        self.hdg_est = HeadingUncertaintyEstimator(self.config)
        self.beh_est = BehaviorUncertaintyEstimator(self.config)
        self.pred_est = PredictionUncertaintyEstimator(self.config)
        self.manager = UncertaintyManager(self.config)

    def _create_mock_track(
        self,
        track_id="TRK_01",
        obj_type=ObjectType.CAR,
        pos=(10.0, 0.0),
        vel=(5.0, 0.0),
        heading=0.0,
        confidence=1.0,
        history=None,
        state=TrackState.CONFIRMED,
    ):
        t = Track(
            track_id=track_id,
            object_type=obj_type,
            current_position=pos,
            velocity=vel,
            speed=math.hypot(vel[0], vel[1]),
            confidence=confidence,
            heading=heading,
        )
        t.state = state
        if history is not None:
            t.history = list(history)
        return t

    # 1. Position Uncertainty — High Confidence
    def test_position_uncertainty_high_confidence(self):
        t = self._create_mock_track(confidence=1.0)
        sx, sy = self.pos_est.estimate(t)
        self.assertLess(sx, 0.3)
        self.assertLess(sy, 0.3)

    # 2. Position Uncertainty — Low Confidence
    def test_position_uncertainty_low_confidence(self):
        t_high = self._create_mock_track(confidence=1.0)
        t_low = self._create_mock_track(confidence=0.3)
        sx_h, sy_h = self.pos_est.estimate(t_high)
        sx_l, sy_l = self.pos_est.estimate(t_low)
        self.assertGreater(sx_l, sx_h)
        self.assertGreater(sy_l, sy_h)

    # 3. Position Uncertainty — Object Type Multiplier
    def test_position_uncertainty_object_type_multiplier(self):
        t_car = self._create_mock_track(obj_type=ObjectType.CAR, confidence=0.8)
        t_cattle = self._create_mock_track(obj_type=ObjectType.CATTLE, confidence=0.8)
        sx_car, sy_car = self.pos_est.estimate(t_car)
        sx_cat, sy_cat = self.pos_est.estimate(t_cattle)
        self.assertGreater(sx_cat, sx_car)

    # 4. Velocity Uncertainty — Constant Speed
    def test_velocity_uncertainty_constant_speed(self):
        hist = [(x, 0.0) for x in range(0, 10)]
        t = self._create_mock_track(history=hist, vel=(1.0, 0.0))
        var = self.vel_est.estimate(t)
        self.assertLess(var, 0.05)

    # 5. Velocity Uncertainty — Erratic Speed
    def test_velocity_uncertainty_erratic_speed(self):
        hist = [(0.0, 0.0), (1.0, 0.0), (1.1, 0.0), (3.5, 0.0), (3.6, 0.0), (7.0, 0.0)]
        t = self._create_mock_track(history=hist, vel=(5.0, 0.0))
        var = self.vel_est.estimate(t)
        self.assertGreater(var, 0.5)

    # 6. Velocity Uncertainty — Insufficient History
    def test_velocity_uncertainty_insufficient_history(self):
        t = self._create_mock_track(history=[(0.0, 0.0)])
        var = self.vel_est.estimate(t)
        self.assertGreater(var, 0.0)

    # 7. Heading Uncertainty — Straight Motion
    def test_heading_uncertainty_straight_motion(self):
        hist = [(x, 0.0) for x in range(0, 10)]
        t = self._create_mock_track(history=hist, heading=0.0)
        h_var = self.hdg_est.estimate(t)
        self.assertLess(h_var, 0.05)

    # 8. Heading Uncertainty — Circular Angular Wrap-Around
    def test_heading_uncertainty_wrap_around(self):
        # Motion crossing +pi -> -pi
        hist = [
            (0.0, 0.0),
            (-0.1, 0.001),
            (-0.2, -0.001),
            (-0.3, 0.002),
        ]
        t = self._create_mock_track(history=hist, heading=math.pi - 0.01)
        h_var = self.hdg_est.estimate(t)
        # Should be small variance (< 0.2 rad²), not ~ 4.0 pi² spurious jump
        self.assertLess(h_var, 0.2)

    # 9. Heading Uncertainty — Erratic Turn
    def test_heading_uncertainty_erratic_turn(self):
        hist = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.0), (3.0, -1.0), (4.0, 0.0)]
        t = self._create_mock_track(history=hist, heading=0.5)
        h_var = self.hdg_est.estimate(t)
        self.assertGreater(h_var, 0.1)

    # 10. Behavior Uncertainty — Single Hypothesis
    def test_behavior_uncertainty_single_hypothesis(self):
        traj = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(1.0, 0.0), (2.0, 0.0)], [0.5, 1.0])
        dis = self.beh_est.estimate([traj], [])
        self.assertEqual(dis, 0.0)

    # 11. Behavior Uncertainty — Multi-Hypothesis Divergence
    def test_behavior_uncertainty_multi_hypothesis_divergence(self):
        t1 = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(5.0, 0.0), (10.0, 0.0)], [0.5, 1.0])
        t2 = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(5.0, 3.0), (10.0, 6.0)], [0.5, 1.0])
        t3 = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(5.0, -3.0), (10.0, -6.0)], [0.5, 1.0])
        h1 = MotionHypothesis(track_id="TRK_01", hypothesis_id="H1", trajectory=t1, behavior_type="FORWARD")
        h2 = MotionHypothesis(track_id="TRK_01", hypothesis_id="H2", trajectory=t2, behavior_type="TURN_LEFT")
        h3 = MotionHypothesis(track_id="TRK_01", hypothesis_id="H3", trajectory=t3, behavior_type="TURN_RIGHT")
        dis = self.beh_est.estimate([], [h1, h2, h3])
        self.assertGreater(dis, 0.3)

    # 12. Behavior Uncertainty — Multi-Hypothesis Parallel
    def test_behavior_uncertainty_multi_hypothesis_parallel(self):
        t1 = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(5.0, 0.0), (10.0, 0.0)], [0.5, 1.0])
        t2 = PredictedTrajectory("TRK_01", ObjectType.CAR, (0.0, 0.0), [(5.0, 0.1), (10.0, 0.1)], [0.5, 1.0])
        h1 = MotionHypothesis(track_id="TRK_01", hypothesis_id="H1", trajectory=t1, behavior_type="FORWARD_1")
        h2 = MotionHypothesis(track_id="TRK_01", hypothesis_id="H2", trajectory=t2, behavior_type="FORWARD_2")
        dis = self.beh_est.estimate([], [h1, h2])
        self.assertLess(dis, 0.1)

    # 13. Prediction Uncertainty — Horizon Growth
    def test_prediction_uncertainty_horizon_growth(self):
        u0 = self.pred_est.estimate(base_uncertainty=0.2, time_horizon=0.0)
        u1 = self.pred_est.estimate(base_uncertainty=0.2, time_horizon=1.0)
        u3 = self.pred_est.estimate(base_uncertainty=0.2, time_horizon=3.0)
        self.assertGreater(u1, u0)
        self.assertGreater(u3, u1)

    # 14. Prediction Uncertainty — Clamping
    def test_prediction_uncertainty_clamping(self):
        u_max = self.pred_est.estimate(base_uncertainty=0.8, time_horizon=10.0)
        self.assertEqual(u_max, 1.0)
        u_min = self.pred_est.estimate(base_uncertainty=-0.5, time_horizon=-2.0)
        self.assertEqual(u_min, 0.0)

    # 15. Tracking Quality Uncertainty — Confirmed vs Lost
    def test_tracking_quality_uncertainty_confirmed_vs_lost(self):
        t_conf = self._create_mock_track(state=TrackState.CONFIRMED)
        t_lost = self._create_mock_track(state=TrackState.LOST)
        u_conf = self.pred_est.estimate_tracking_uncertainty(t_conf)
        u_lost = self.pred_est.estimate_tracking_uncertainty(t_lost)
        self.assertLess(u_conf, u_lost)

    # 16. Uncertainty Ellipse Generation
    def test_uncertainty_ellipse_generation(self):
        ellipse = self.manager._build_ellipse((10.0, 2.0), sigma_x=0.5, sigma_y=0.2, heading=0.1, t_horizon=0.0)
        self.assertEqual(ellipse.center, (10.0, 2.0))
        self.assertGreaterEqual(ellipse.semi_major, 0.5)
        self.assertGreaterEqual(ellipse.semi_minor, 0.2)
        self.assertEqual(ellipse.orientation, 0.1)

    # 17. Uncertainty Ellipse Horizon Expansion
    def test_uncertainty_ellipse_horizon_expansion(self):
        e0 = self.manager._build_ellipse((10.0, 2.0), sigma_x=0.5, sigma_y=0.2, heading=0.0, t_horizon=0.0)
        e3 = self.manager._build_ellipse((10.0, 2.0), sigma_x=0.5, sigma_y=0.2, heading=0.0, t_horizon=3.0)
        self.assertGreater(e3.semi_major, e0.semi_major)
        self.assertGreater(e3.semi_minor, e0.semi_minor)

    # 18. Uncertainty Region Object Binding
    def test_uncertainty_region_object_binding(self):
        t = self._create_mock_track()
        u_set = self.manager.evaluate_uncertainty([t], current_time=0.0)
        self.assertEqual(len(u_set.regions), 1)
        region = u_set.regions[0]
        self.assertEqual(region.track_id, "TRK_01")
        self.assertEqual(region.object_type, ObjectType.CAR)
        self.assertIsNotNone(region.current_ellipse)
        self.assertGreater(len(region.future_ellipses), 0)

    # 19. Uncertainty Grid Construction
    def test_uncertainty_grid_construction(self):
        grid = UncertaintyGrid(num_cols=100, num_rows=40, resolution=0.5)
        self.assertEqual(grid.uncertainty_matrix.shape, (40, 100))
        self.assertTrue(np.all(grid.uncertainty_matrix == 0.0))

    # 20. Uncertainty Grid Ellipse Rasterization
    def test_uncertainty_grid_ellipse_rasterization(self):
        converter = CoordinateConverter(ppm=20.0, grid_res=0.5)
        grid = UncertaintyGrid(num_cols=100, num_rows=40, resolution=0.5)
        ellipse = UncertaintyEllipse(center=(10.0, 0.0), semi_major=1.5, semi_minor=1.0, orientation=0.0)
        grid.rasterize_ellipse(ellipse, converter, peak_uncertainty=0.8)
        self.assertGreater(grid.get_max_uncertainty(), 0.0)
        r, c = converter.world_to_grid(10.0, 0.0)
        self.assertGreater(grid.get_uncertainty(r, c), 0.5)

    # 21. Uncertainty Manager Evaluate
    def test_uncertainty_manager_evaluate(self):
        t1 = self._create_mock_track("TRK_01")
        t2 = self._create_mock_track("TRK_02", obj_type=ObjectType.CATTLE, pos=(20.0, 1.0))
        u_set = self.manager.evaluate_uncertainty([t1, t2], current_time=0.0)
        self.assertEqual(len(u_set.regions), 2)
        self.assertIsNotNone(u_set.timestamp)

    # 22. Uncertainty Manager Summary
    def test_uncertainty_manager_summary(self):
        t1 = self._create_mock_track("TRK_01")
        self.manager.evaluate_uncertainty([t1], current_time=0.0)
        summary = self.manager.get_summary()
        self.assertIn("active_regions", summary)
        self.assertIn("avg_overall_uncertainty", summary)
        self.assertEqual(summary["active_regions"], 1)

    # 23. World Model Uncertainty Integration
    def test_world_model_uncertainty_integration(self):
        world_model = WorldModel()
        env = SimulationEnvironment()
        t1 = self._create_mock_track("TRK_01")
        world_model.update_from_environment(
            env,
            tracks=[t1],
            uncertainty_manager=self.manager,
        )
        self.assertIsNotNone(world_model.uncertainty_set)
        self.assertIsNotNone(world_model.uncertainty_grid)
        self.assertEqual(len(world_model.uncertainty_set.regions), 1)

    # 24. Uncertainty and Risk Separation (Preserve Phase 4 Risk Engine Unmodified)
    def test_uncertainty_and_risk_separation(self):
        world_model = WorldModel()
        env = SimulationEnvironment()
        t1 = self._create_mock_track("TRK_01")
        world_model.update_from_environment(
            env,
            tracks=[t1],
            uncertainty_manager=self.manager,
        )
        # Verify uncertainty_set and risk_grid are distinct modules and attributes
        self.assertIsNotNone(world_model.uncertainty_set)
        self.assertFalse(hasattr(world_model.uncertainty_set, "total_risk"))
        self.assertTrue(hasattr(world_model.grid, "rasterize_oriented_box"))


if __name__ == "__main__":
    unittest.main()
