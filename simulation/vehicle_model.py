"""
IRIS Kinematic Vehicle Model and State Management.
Implements physically consistent 2D kinematic bicycle model with rate-limited steering,
proper heading-driven physics, and safety-checker integration.
"""

import math
from dataclasses import dataclass
from typing import Tuple, List, Optional, Any
import numpy as np

from simulation.vehicle_safety import VehicleSafetyChecker, VehicleCondition, FootprintCheckResult

# Physical Vehicle Constraints
WHEELBASE = 2.8           # meters
VEHICLE_LENGTH = 4.6      # meters
VEHICLE_WIDTH = 2.0       # meters
MAX_STEERING_ANGLE = 0.5  # radians (~28.6 deg)
MAX_STEERING_RATE = 0.8   # radians/second
MAX_ACCELERATION = 3.5    # m/s^2
MAX_BRAKING = 8.0         # m/s^2
MAX_SPEED = 25.0          # m/s (~90 km/h)
MIN_SPEED = -3.0          # m/s (reverse max)


@dataclass
class VehicleState:
    position: Tuple[float, float]  # (x, y) in meters
    heading: float                 # radians
    speed: float                   # m/s (velocity)
    acceleration: float            # m/s^2
    steering_angle: float          # radians
    angular_velocity: float        # radians/s (yaw rate)


@dataclass
class VehicleControl:
    target_speed: float            # m/s
    steering: float                # normalized [-1.0, 1.0] or radians
    acceleration: float            # m/s^2
    brake: float                   # m/s^2


class KinematicBicycleVehicle:
    """
    Physically consistent 2D Kinematic Bicycle Model.
    Governing Equations:
      dot(x) = v * cos(heading)
      dot(y) = v * sin(heading)
      dot(heading) = (v / wheelbase) * tan(steering_angle)
      dot(v) = acceleration - brake
    """

    def __init__(
        self,
        x: float = 5.0,
        y: float = 0.0,
        heading: float = 0.0,
        velocity: float = 0.0,
        wheelbase: float = WHEELBASE,
        length: float = VEHICLE_LENGTH,
        width: float = VEHICLE_WIDTH,
    ):
        self.x = float(x)
        self.y = float(y)
        self.heading = float(heading)
        self.velocity = float(velocity)
        self.acceleration = 0.0
        self.steering_angle = 0.0
        self.angular_velocity = 0.0

        self.wheelbase = wheelbase
        self.length = length
        self.width = width

        # Controllers & Safety
        self.safety_checker = VehicleSafetyChecker(
            road_width=12.0,
            road_length=300.0,
            vehicle_length=length,
            vehicle_width=width,
        )
        self.condition = VehicleCondition.NORMAL
        self.last_safety_result: Optional[FootprintCheckResult] = None
        self.replanning_requested: bool = False

        # Phase metadata
        self.target_speed = velocity
        self.decision_state = "NORMAL_DRIVING"
        self.current_path = None
        self.travel_time = 0.0
        self.path_length = 0.0
        self.goal_reached = False
        self.braking_state = "CRUISING"
        self.lookahead_point = (x + 5.0, y)

    @property
    def speed(self) -> float:
        return self.velocity

    @speed.setter
    def speed(self, val: float):
        self.velocity = val

    def get_state(self) -> VehicleState:
        return VehicleState(
            position=(self.x, self.y),
            heading=self.heading,
            speed=self.velocity,
            acceleration=self.acceleration,
            steering_angle=self.steering_angle,
            angular_velocity=self.angular_velocity,
        )

    def get_corners(self) -> List[Tuple[float, float]]:
        """Returns 4 corner vertices (x, y) of oriented bounding box in meters."""
        return self.safety_checker.get_vehicle_footprint(
            self.x, self.y, self.heading, self.length, self.width
        )

    def update(
        self,
        dt: float,
        throttle: float,
        steering: float,
        traffic_actors: Optional[List[Any]] = None,
        surface_hazards: Optional[List[Any]] = None,
        future_risk: float = 0.0,
    ) -> FootprintCheckResult:
        """
        Executes one physically consistent kinematic bicycle step with rate limits
        and road boundary safety checks.
        :param dt: timestep in seconds
        :param throttle: command [-1.0 (max brake) to +1.0 (max accel)]
        :param steering: command [-1.0 (max left) to +1.0 (max right)]
        """
        self.travel_time += dt

        # 1. Target Steering with rate-limiting
        target_steer = float(np.clip(steering * MAX_STEERING_ANGLE, -MAX_STEERING_ANGLE, MAX_STEERING_ANGLE))
        max_steer_delta = MAX_STEERING_RATE * dt
        steer_diff = target_steer - self.steering_angle
        steer_diff_clamped = float(np.clip(steer_diff, -max_steer_delta, max_steer_delta))
        self.steering_angle += steer_diff_clamped

        # 2. Acceleration / Braking command
        if throttle >= 0.0:
            target_accel = throttle * MAX_ACCELERATION
        else:
            target_accel = throttle * MAX_BRAKING  # Negative for braking

        self.acceleration = float(np.clip(target_accel, -MAX_BRAKING, MAX_ACCELERATION))

        # 3. Proposed Velocity
        prop_v = self.velocity + self.acceleration * dt
        prop_v = float(np.clip(prop_v, MIN_SPEED, MAX_SPEED))

        # 4. Kinematic state propagation
        # Yaw rate: omega = (v / L) * tan(delta)
        yaw_rate = (prop_v / self.wheelbase) * math.tan(self.steering_angle)
        self.angular_velocity = yaw_rate

        prop_heading = self.heading + yaw_rate * dt
        # Normalize heading to [-pi, pi]
        prop_heading = (prop_heading + math.pi) % (2 * math.pi) - math.pi

        prop_dx = prop_v * math.cos(prop_heading) * dt
        prop_dy = prop_v * math.sin(prop_heading) * dt

        prop_x = self.x + prop_dx
        prop_y = self.y + prop_dy

        # 5. Proposed Footprint Safety Check
        prop_footprint = self.safety_checker.get_vehicle_footprint(
            prop_x, prop_y, prop_heading, self.length, self.width
        )

        ttc = 999.0
        if self.velocity > 0.1 and traffic_actors:
            min_dist = 999.0
            for a in traffic_actors:
                ax = getattr(a, "x", 0.0)
                ay = getattr(a, "y", 0.0)
                if ax > self.x and abs(ay - self.y) < 2.5:
                    d = ax - self.x
                    if d < min_dist:
                        min_dist = d
            if min_dist < 100.0:
                ttc = min_dist / self.velocity

        safety_res = self.safety_checker.is_footprint_safe(
            prop_footprint,
            traffic_actors=traffic_actors,
            surface_hazards=surface_hazards,
            ttc=ttc,
            future_risk=future_risk,
            speed=prop_v,
        )

        # 6. Safety Enforcement & Intervention
        if not safety_res.inside_road:
            # Prevent leaving the road! Constrain lateral position and steer away from boundary
            self.replanning_requested = True
            # Clamp Y within road envelope
            safe_half_w = self.width / 2.0 + 0.1
            prop_y = float(np.clip(prop_y, self.safety_checker.y_min + safe_half_w, self.safety_checker.y_max - safe_half_w))
            # Turn heading back parallel to road (heading -> 0)
            prop_heading = prop_heading * 0.5
            prop_v = max(0.0, prop_v * 0.7)  # Brake on near-edge violation
            self.condition = VehicleCondition.CAUTION
        elif safety_res.collision_detected or safety_res.condition == VehicleCondition.NEAR_COLLISION:
            # Emergency braking
            self.replanning_requested = True
            prop_v = max(0.0, self.velocity - MAX_BRAKING * dt)
            self.condition = VehicleCondition.NEAR_COLLISION
        elif safety_res.condition == VehicleCondition.SLOW_DOWN:
            prop_v = min(prop_v, 6.0)
            self.condition = VehicleCondition.SLOW_DOWN
        else:
            self.condition = safety_res.condition

        # Apply state update
        self.x = prop_x
        self.y = prop_y
        self.heading = prop_heading
        self.velocity = prop_v
        self.path_length += float(math.hypot(prop_dx, prop_dy))
        self.last_safety_result = safety_res

        return safety_res
