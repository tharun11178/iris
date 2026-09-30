"""
IRIS — Indian Road Intelligence & Safe-space Planner
Phase 12: Adaptive Replanning & Dynamic Path Management Unit Tests
"""

import unittest
import math
from replanning.config import ReplanningConfig
from replanning.path_state import CurrentPathState, ReplanningStatus, ReplanReason, ReplanningDecision
from replanning.path_monitor import PathMonitor
from replanning.trigger_detector import TriggerDetector
from replanning.path_transition import PathTransitionManager
from replanning.replanning_manager import ReplanningManager
from safe_space.safe_space_planner import SafeSpacePlanner
from world.world_model import WorldModel
from risk_engine.risk_grid import RiskGrid
from future_risk.future_risk_engine import FutureRiskEngine, FutureRiskField


class MockPath:
    def __init__(self, world_points, valid=True, cost=10.0):
        self.world_points = world_points
        self.valid = valid
        self.cost = cost
        self.success = valid
        self.length = len(world_points) * 1.0
        self.status_message = "MOCK_PATH"

    def get_current_waypoint(self, x, y):
        if not self.world_points:
            return None
        return self.world_points[0]


class TestReplanningPipeline(unittest.TestCase):
    def setUp(self):
        self.config = ReplanningConfig(
            min_replan_interval=0.5,
            min_improvement_required=0.15,
            path_degradation_threshold=0.25,
            max_deviation_distance=2.5,
            high_risk_threshold=0.75,
        )
        self.planner = SafeSpacePlanner(mode="iris_safe_space")
        self.replanning_manager = ReplanningManager(planner=self.planner)
        self.world_model = WorldModel()
        grid = RiskGrid(
            num_rows=self.world_model.grid.num_rows,
            num_cols=self.world_model.grid.num_cols,
            grid_res=self.world_model.converter.grid_res
        )
        self.future_risk_field = FutureRiskField(timestamp=0.0, risk_grids=[grid], timestamps=[0.0])

    def test_config_defaults(self):
        cfg = ReplanningConfig()
        self.assertGreater(cfg.min_replan_interval, 0.0)
        self.assertGreater(cfg.min_improvement_required, 0.0)
        self.assertGreater(cfg.max_deviation_distance, 0.0)

    def test_path_state_initialization(self):
        pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        path = MockPath(pts, valid=True, cost=12.0)
        state = CurrentPathState(path=path, original_score=12.0, current_score=12.0, creation_time=1.0)

        self.assertTrue(state.path_valid)
        self.assertEqual(state.path_id, "PATH_INITIAL")

    def test_path_monitor_invalidation(self):
        monitor = PathMonitor()
        pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        path = MockPath(pts, valid=False, cost=10.0)
        path.success = False
        state = CurrentPathState(path=path, original_score=10.0, path_valid=False)

        updated_state = monitor.monitor_path(state, self.world_model, self.future_risk_field, (0.0, 0.0))
        self.assertFalse(updated_state.path_valid)

    def test_trigger_detector_hard_priority(self):
        detector = TriggerDetector()
        pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        path = MockPath(pts, valid=False, cost=10.0)
        state = CurrentPathState(path=path, original_score=10.0, path_valid=False)

        decision = detector.detect_trigger(state, self.world_model, self.future_risk_field, current_time=2.0)
        self.assertTrue(decision.should_replan)
        self.assertTrue(decision.is_hard_trigger)
        self.assertEqual(decision.reason, ReplanReason.PATH_BLOCKED)

    def test_trigger_detector_hysteresis_prevention(self):
        detector = TriggerDetector(min_replan_interval=1.0)
        pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0)]
        path = MockPath(pts, valid=True, cost=10.0)
        state = CurrentPathState(path=path, original_score=10.0, current_score=20.0, path_degraded=True, last_replan_time=1.0)

        # Soft trigger evaluation at t=1.2s (interval 0.2s < 1.0s cooldown)
        decision = detector.detect_trigger(state, self.world_model, self.future_risk_field, current_time=1.2)
        self.assertFalse(decision.should_replan)

    def test_path_transition_manager_smooth_blend(self):
        transition_mgr = PathTransitionManager()
        old_pts = [(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (6.0, 0.0)]
        new_pts = [(0.0, 1.0), (2.0, 1.0), (4.0, 1.0), (6.0, 1.0)]

        new_path = MockPath(new_pts)

        transition_path = transition_mgr.create_transition_path(
            ego_pos=(0.0, 0.0),
            new_path=new_path,
            world_model=self.world_model
        )

        self.assertIsNotNone(transition_path)
        self.assertTrue(len(transition_path.world_points) >= 4)

    def test_replanning_manager_full_cycle(self):
        pts = [(0.0, 0.0), (5.0, 0.0), (10.0, 0.0), (15.0, 0.0), (20.0, 0.0)]
        path = MockPath(pts, valid=True, cost=10.0)

        self.replanning_manager.initialize_path(path, self.world_model, creation_reason="INITIAL", score=10.0)
        self.assertEqual(self.replanning_manager.status, ReplanningStatus.FOLLOWING_PATH)

        # Invalidate path to trigger HARD replan
        path.valid = False
        path.success = False
        decision = self.replanning_manager.evaluate(
            world_model=self.world_model,
            future_risk_field=self.future_risk_field,
            current_time=1.0,
            goal_pos=(20.0, 0.0)
        )

        self.assertIsNotNone(decision)
        self.assertTrue(decision.should_replan)
        self.assertTrue(decision.is_hard_trigger)

        metrics = self.replanning_manager.get_metrics()
        self.assertEqual(metrics.total_replans, 1)
        self.assertEqual(metrics.hard_trigger_replans, 1)

    def test_safety_hold_fallback(self):
        pts = [(0.0, 0.0), (5.0, 0.0)]
        path = MockPath(pts, valid=False, cost=10.0)

        class FailingPlanner:
            def plan(self, *args, **kwargs):
                class DummyRes:
                    selected_path = None
                    selected_corridor = None
                    reason = "NO_SAFE_CORRIDOR"
                    success = False
                return DummyRes()

        failing_mgr = ReplanningManager(planner=FailingPlanner())
        failing_mgr.initialize_path(path, self.world_model, creation_reason="INITIAL", score=10.0)

        path.valid = False
        path.success = False
        decision = failing_mgr.evaluate(
            world_model=self.world_model,
            future_risk_field=self.future_risk_field,
            current_time=1.0,
            goal_pos=(10.0, 0.0)
        )

        self.assertEqual(failing_mgr.status, ReplanningStatus.SAFETY_HOLD)
        self.assertEqual(decision.reason, ReplanReason.REPLAN_FAILED)


if __name__ == "__main__":
    unittest.main()
