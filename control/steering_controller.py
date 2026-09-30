"""
IRIS Steering Controller — Pure Pursuit Baseline (Combined Phase 13).
Geometric path-following controller finding dynamic lookahead target on active path
and computing steering angle command delta.
"""

import math
from typing import Tuple, Optional, List, Any
from planning.path import Path
from control.config import (
    WHEELBASE,
    LOOKAHEAD_DISTANCE,
    MIN_LOOKAHEAD,
    MAX_LOOKAHEAD,
    LOOKAHEAD_GAIN,
    MAX_STEERING_ANGLE,
)


class SteeringController:
    """
    Pure Pursuit Baseline Geometric Steering Controller.
    """

    def __init__(self, wheelbase: float = WHEELBASE, lookahead_gain: float = LOOKAHEAD_GAIN):
        self.wheelbase = wheelbase
        self.lookahead_gain = lookahead_gain

    def compute_steering(
        self,
        vehicle_position: Tuple[float, float],
        vehicle_heading: float,
        current_speed: float,
        current_path: Optional[Path],
        override_lookahead: Optional[float] = None,
    ) -> Tuple[float, Tuple[float, float]]:
        """
        Computes steering angle in radians and returns (steering_angle, lookahead_point).
        """
        ego_x, ego_y = vehicle_position

        # Fallback if path is missing or empty
        if current_path is None or not current_path.world_points:
            return 0.0, (ego_x + 5.0 * math.cos(vehicle_heading), ego_y + 5.0 * math.sin(vehicle_heading))

        world_pts = current_path.world_points

        # 1. Calculate Dynamic Lookahead Distance L_d
        if override_lookahead is not None and override_lookahead > 0.0:
            L_d = override_lookahead
        else:
            L_d = MIN_LOOKAHEAD + self.lookahead_gain * abs(current_speed)
            L_d = max(MIN_LOOKAHEAD, min(MAX_LOOKAHEAD, L_d))

        # 2. Find closest point on path to ego vehicle
        closest_idx = 0
        min_dist = 9999.0
        for i, (wx, wy) in enumerate(world_pts):
            d = math.hypot(wx - ego_x, wy - ego_y)
            if d < min_dist:
                min_dist = d
                closest_idx = i

        # 3. Find lookahead target point at distance >= L_d along path
        target_pt = world_pts[-1]
        for i in range(closest_idx, len(world_pts)):
            wx, wy = world_pts[i]
            d = math.hypot(wx - ego_x, wy - ego_y)
            if d >= L_d:
                target_pt = (wx, wy)
                break

        # 4. Pure Pursuit Curvature & Steering Angle Calculation
        tx, ty = target_pt
        dx = tx - ego_x
        dy = ty - ego_y

        target_heading = math.atan2(dy, dx)
        alpha = target_heading - vehicle_heading

        # Normalize alpha to [-pi, pi]
        alpha = (alpha + math.pi) % (2 * math.pi) - math.pi

        # Actual distance to target point
        actual_dist = max(0.5, math.hypot(dx, dy))

        # Curvature kappa = (2 * sin(alpha)) / L_d
        kappa = (2.0 * math.sin(alpha)) / actual_dist

        # Steering angle delta = arctan(kappa * wheelbase)
        steering_angle = math.atan(kappa * self.wheelbase)

        # Clip steering angle to physical limits [-MAX_STEERING_ANGLE, +MAX_STEERING_ANGLE]
        steering_angle = float(max(-MAX_STEERING_ANGLE, min(MAX_STEERING_ANGLE, steering_angle)))

        return steering_angle, target_pt
