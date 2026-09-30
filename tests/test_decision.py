"""
IRIS — Indian Road Intelligence & Safe-space Planner
Phase 13: Decision & Emergency Safety Unit Tests
"""

import unittest
import math
from decision.config import (
    CRITICAL_RISK_THRESHOLD,
    HIGH_RISK_THRESHOLD,
    HARD_CLEARANCE_VIOLATION,
    LOW_CLEARANCE_THRESHOLD,
    GOAL_TOLERANCE_DISTANCE,
)
from decision.decision_state import DecisionState, DecisionResult
from decision.emergency_safety import EmergencySafetyManager
from decision.decision_manager import DecisionManager
from replanning.path_state import ReplanningStatus, CurrentPathState
from world.world_model import WorldModel


class TestDecisionAndEmergencySafety(unittest.TestCase):
    def setUp(self):
        self.world_model = WorldModel()
        self.decision_manager = DecisionManager()
        self.emergency_safety = EmergencySafetyManager()

    def test_normal_driving_decision(self):
        res = self.decision_manager.evaluate_decision(
            world_model=self.world_model,
            future_risk_field=None,
            replanning_manager=None,
            current_time=0.0,
            goal_pos=(100.0, 0.0),
        )
        self.assertEqual(res.state, DecisionState.NORMAL_DRIVING)
        self.assertEqual(res.target_speed_factor, 1.0)
        self.assertEqual(res.priority_level, 6)

    def test_emergency_safety_hard_clearance_violation(self):
        is_emergency, res = self.emergency_safety.check_emergency_stop(
            world_model=self.world_model,
            min_clearance=0.5,  # < HARD_CLEARANCE_VIOLATION (0.8m)
            peak_future_risk=0.1,
            path_valid=True,
        )
        self.assertTrue(is_emergency)
        self.assertEqual(res.state, DecisionState.STOP)
        self.assertEqual(res.override_reason, "HARD_CLEARANCE_VIOLATION")

    def test_emergency_safety_critical_collision_risk(self):
        is_emergency, res = self.emergency_safety.check_emergency_stop(
            world_model=self.world_model,
            min_clearance=2.0,
            peak_future_risk=0.90,  # >= CRITICAL_RISK_THRESHOLD (0.85)
            path_valid=True,
        )
        self.assertTrue(is_emergency)
        self.assertEqual(res.state, DecisionState.STOP)
        self.assertEqual(res.override_reason, "CRITICAL_COLLISION_RISK")

    def test_emergency_safety_safety_hold_no_replacement(self):
        is_emergency, res = self.emergency_safety.check_emergency_stop(
            world_model=self.world_model,
            min_clearance=2.0,
            peak_future_risk=0.1,
            path_valid=False,
            replanning_status=ReplanningStatus.SAFETY_HOLD,
        )
        self.assertTrue(is_emergency)
        self.assertEqual(res.state, DecisionState.SAFETY_HOLD)
        self.assertEqual(res.override_reason, "NO_SAFE_REPLACEMENT_PATH")

    def test_goal_reached_decision(self):
        # Position ego close to goal (1.0m < 2.0m tolerance)
        ego_pos = self.world_model.converter.sim_to_world(5.0, 0.0)
        goal_pos = (ego_pos[0] + 1.0, ego_pos[1])

        res = self.decision_manager.evaluate_decision(
            world_model=self.world_model,
            goal_pos=goal_pos,
            current_time=10.0,
        )
        self.assertEqual(res.state, DecisionState.GOAL_REACHED)
        self.assertEqual(res.target_speed_factor, 0.0)

    def test_slow_down_on_high_risk(self):
        # Mock class holding current path state metrics
        class MockReplanningManager:
            def __init__(self):
                self.current_state = CurrentPathState(
                    minimum_clearance=2.0,
                    current_peak_risk=0.75,  # >= HIGH_RISK_THRESHOLD
                    path_valid=True,
                )
                self.status = ReplanningStatus.FOLLOWING_PATH

        res = self.decision_manager.evaluate_decision(
            world_model=self.world_model,
            replanning_manager=MockReplanningManager(),
            goal_pos=(200.0, 0.0),
        )
        self.assertEqual(res.state, DecisionState.SLOW_DOWN)
        self.assertLess(res.target_speed_factor, 0.5)

    def test_caution_on_low_clearance(self):
        class MockReplanningManager:
            def __init__(self):
                self.current_state = CurrentPathState(
                    minimum_clearance=1.0,  # < LOW_CLEARANCE_THRESHOLD (1.2m)
                    current_peak_risk=0.2,
                    path_valid=True,
                )
                self.status = ReplanningStatus.FOLLOWING_PATH

        res = self.decision_manager.evaluate_decision(
            world_model=self.world_model,
            replanning_manager=MockReplanningManager(),
            goal_pos=(200.0, 0.0),
        )
        self.assertEqual(res.state, DecisionState.SLOW_DOWN)


if __name__ == "__main__":
    unittest.main()
