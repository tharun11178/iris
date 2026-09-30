"""
IRIS — Indian Road Intelligence & Safe-space Planner
Phase 13: Vehicle Control Unit & Integration Tests
"""

import unittest
import math
from control.config import (
    MAX_SPEED,
    NOMINAL_TARGET_SPEED,
    MAX_ACCELERATION,
    MAX_DECELERATION,
    MAX_STEERING_ANGLE,
)
from control.speed_controller import SpeedController
from control.steering_controller import SteeringController
from control.longitudinal_controller import LongitudinalController
from control.vehicle_controller import VehicleController, ControlCommand
from decision.decision_state import DecisionState
from planning.path import Path
from world.world_model import WorldModel


class MockPath:
    def __init__(self, world_points, valid=True, cost=10.0):
        self.world_points = world_points
        self.valid = valid
        self.cost = cost
        self.success = valid
        self.length = len(world_points) * 1.0

    def get_current_waypoint(self, x, y):
        if not self.world_points:
            return None
        return self.world_points[0]


class TestVehicleControlPipeline(unittest.TestCase):
    def setUp(self):
        self.world_model = WorldModel()
        self.speed_controller = SpeedController()
        self.steering_controller = SteeringController()
        self.longitudinal_controller = LongitudinalController()
        self.vehicle_controller = VehicleController()

    def test_speed_controller_risk_reduction(self):
        # Low risk -> Nominal speed
        v_low = self.speed_controller.compute_target_speed(
            current_speed=5.0,
            decision_state=DecisionState.NORMAL_DRIVING,
            future_risk=0.1,
            minimum_clearance=2.5,
        )
        self.assertGreater(v_low, 6.0)

        # High risk -> Reduced speed
        v_high = self.speed_controller.compute_target_speed(
            current_speed=5.0,
            decision_state=DecisionState.SLOW_DOWN,
            future_risk=0.8,
            minimum_clearance=1.0,
        )
        self.assertLess(v_high, v_low)

        # Stop decision state -> 0.0 m/s
        v_stop = self.speed_controller.compute_target_speed(
            current_speed=5.0,
            decision_state=DecisionState.STOP,
        )
        self.assertEqual(v_stop, 0.0)

    def test_pure_pursuit_steering_straight_line(self):
        # Straight line path along X axis
        pts = [(i * 2.0, 0.0) for i in range(20)]
        path = MockPath(pts)

        steer_angle, lookahead = self.steering_controller.compute_steering(
            vehicle_position=(0.0, 0.0),
            vehicle_heading=0.0,
            current_speed=5.0,
            current_path=path,
        )
        # On straight line with zero heading error, steering angle should be near 0
        self.assertAlmostEqual(steer_angle, 0.0, places=2)
        self.assertGreater(lookahead[0], 0.0)

    def test_pure_pursuit_steering_curved_road(self):
        # Curve turning to the left (+Y)
        pts = [(i * 2.0, i * 0.5) for i in range(20)]
        path = MockPath(pts)

        steer_angle, lookahead = self.steering_controller.compute_steering(
            vehicle_position=(0.0, 0.0),
            vehicle_heading=0.0,
            current_speed=5.0,
            current_path=path,
        )
        # Turning left -> positive steering angle
        self.assertGreater(steer_angle, 0.0)

    def test_longitudinal_controller_acceleration_limits(self):
        # Target higher than current -> positive accel bounded by MAX_ACCELERATION
        accel, throttle, state = self.longitudinal_controller.compute_longitudinal_control(
            current_speed=2.0,
            target_speed=8.0,
            dt=0.1,
        )
        self.assertGreater(accel, 0.0)
        self.assertLessEqual(accel, MAX_ACCELERATION)
        self.assertEqual(state, "ACCELERATING")

        # Target lower than current -> braking bounded by MAX_DECELERATION
        accel_b, throttle_b, state_b = self.longitudinal_controller.compute_longitudinal_control(
            current_speed=8.0,
            target_speed=2.0,
            dt=0.1,
        )
        self.assertLess(accel_b, 0.0)
        self.assertGreaterEqual(accel_b, MAX_DECELERATION)

        # Emergency stop -> Hard deceleration
        accel_e, throttle_e, state_e = self.longitudinal_controller.compute_longitudinal_control(
            current_speed=8.0,
            target_speed=0.0,
            dt=0.1,
            is_emergency=True,
        )
        self.assertEqual(state_e, "EMERGENCY_STOP")
        self.assertEqual(throttle_e, -1.0)

    def test_vehicle_controller_scenarios(self):
        # Scenario 1: Empty Road / Normal Navigation
        cmd_empty = self.vehicle_controller.compute_control(
            world_model=self.world_model,
            goal_pos=(100.0, 0.0),
        )
        self.assertEqual(cmd_empty.decision_result.state, DecisionState.NORMAL_DRIVING)
        self.assertGreater(cmd_empty.target_speed, 0.0)

        # Scenario 2: Goal Reached
        ego_pos = self.world_model.converter.sim_to_world(5.0, 0.0)
        cmd_goal = self.vehicle_controller.compute_control(
            world_model=self.world_model,
            goal_pos=(ego_pos[0] + 1.0, ego_pos[1]),  # Within 2m tolerance
        )
        self.assertEqual(cmd_goal.decision_result.state, DecisionState.GOAL_REACHED)
        self.assertEqual(cmd_goal.target_speed, 0.0)


if __name__ == "__main__":
    unittest.main()
