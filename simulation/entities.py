"""
Core Entity Definitions for IRIS Simulation (Phase 1).
Defines object models for Road, Ego Vehicle, Dynamic Traffic Actors, and Surface Hazards.
"""

from enum import Enum, auto
import math
import numpy as np
from configs.sim_config import ACTOR_SPECS, EGO_LENGTH, EGO_WIDTH, EGO_MAX_SPEED, EGO_MIN_SPEED, EGO_MAX_ACCEL, EGO_MAX_BRAKE, EGO_MAX_STEER


class ActorType(Enum):
    EGO = auto()
    CAR = auto()
    BUS_TRUCK = auto()
    AUTO_RICKSHAW = auto()
    MOTORCYCLE = auto()
    BICYCLE = auto()
    PEDESTRIAN = auto()
    CATTLE = auto()
    PUSHCART = auto()


class HazardType(Enum):
    POTHOLE = auto()
    WATERLOGGED = auto()
    SPEED_BREAKER = auto()
    DEBRIS = auto()
    ROAD_DEPRESSION = auto()


class BehaviorMode(Enum):
    CRUISE = auto()
    LANE_FOLLOW = auto()
    SWERVING = auto()
    CROSSING = auto()
    STOPPED = auto()
    WRONG_SIDE = auto()


class SurfaceHazard:
    """
    Represents static or quasi-static road surface features.
    """
    def __init__(self, hazard_id: int, hazard_type: HazardType, x: float, y: float, 
                 length: float, width: float, severity: float = 0.5, uncertainty: float = 0.1):
        self.hazard_id = hazard_id
        self.hazard_type = hazard_type
        self.x = x            # Longitudinal center position in meters
        self.y = y            # Lateral center position in meters
        self.length = length  # Along road X (meters)
        self.width = width    # Across road Y (meters)
        self.severity = severity        # 0.0 (minor) to 1.0 (severe hazard)
        self.uncertainty = uncertainty  # 0.0 (high confidence) to 1.0 (uncertain surface)

    def get_bounding_box(self):
        """Returns (min_x, max_x, min_y, max_y) in world meters."""
        half_l = self.length / 2.0
        half_w = self.width / 2.0
        return (self.x - half_l, self.x + half_l, self.y - half_w, self.y + half_w)


class TrafficActor:
    """
    Represents dynamic road users (Vehicles, Autos, Motorcycles, Pedestrians, Cattle, Pushcarts).
    """
    def __init__(self, actor_id: int, actor_type: ActorType, x: float, y: float, 
                 heading: float = 0.0, velocity: float = 0.0, behavior: BehaviorMode = BehaviorMode.CRUISE):
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.x = x
        self.y = y
        self.heading = heading  # radians (0 = along +X road direction)
        self.velocity = velocity  # m/s
        self.behavior = behavior

        # Fetch default physical dimensions based on actor type
        type_str = actor_type.name
        specs = ACTOR_SPECS.get(type_str, {"length": 2.0, "width": 1.0, "max_speed": 10.0})
        self.length = specs["length"]
        self.width = specs["width"]
        self.max_speed = specs["max_speed"]

        # Behavior parameters
        self.time_offset = np.random.uniform(0.0, 10.0)

    def update(self, dt: float, sim_time: float):
        """Update traffic actor position based on behavior mode."""
        if self.behavior == BehaviorMode.CRUISE or self.behavior == BehaviorMode.LANE_FOLLOW:
            # Move straight along heading
            self.x += self.velocity * math.cos(self.heading) * dt
            self.y += self.velocity * math.sin(self.heading) * dt

        elif self.behavior == BehaviorMode.CROSSING:
            # Pedestrian or Cattle crossing road laterally
            self.x += self.velocity * math.cos(self.heading) * dt
            self.y += self.velocity * math.sin(self.heading) * dt

        elif self.behavior == BehaviorMode.SWERVING:
            # Unstructured Indian road behavior: slight sinusoidal lateral swerving
            swerve = 0.8 * math.sin(1.2 * sim_time + self.time_offset)
            current_heading = self.heading + swerve * 0.15
            self.x += self.velocity * math.cos(current_heading) * dt
            self.y += self.velocity * math.sin(current_heading) * dt

        elif self.behavior == BehaviorMode.WRONG_SIDE:
            # Moving opposite to normal road direction
            self.x += self.velocity * math.cos(self.heading) * dt
            self.y += self.velocity * math.sin(self.heading) * dt

        elif self.behavior == BehaviorMode.STOPPED:
            pass

    def get_corners(self):
        """Returns 4 corner vertices (x, y) of oriented bounding box in world meters."""
        half_l = self.length / 2.0
        half_w = self.width / 2.0
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)

        # Corners relative to center
        rel_corners = [
            (half_l, half_w),
            (half_l, -half_w),
            (-half_l, -half_w),
            (-half_l, half_w)
        ]

        # Rotate and translate
        world_corners = []
        for rx, ry in rel_corners:
            wx = self.x + (rx * cos_h - ry * sin_h)
            wy = self.y + (rx * sin_h + ry * cos_h)
            world_corners.append((wx, wy))

        return world_corners


class EgoVehicle:
    """
    Represents the IRIS autonomous vehicle (kinematic vehicle model).
    """
    def __init__(self, x: float = 0.0, y: float = 0.0, heading: float = 0.0, velocity: float = 0.0):
        self.x = x
        self.y = y
        self.heading = heading        # Yaw angle in radians
        self.velocity = velocity      # m/s
        self.acceleration = 0.0       # m/s^2
        self.steering_angle = 0.0     # radians

        self.length = EGO_LENGTH
        self.width = EGO_WIDTH

        # Phase 13 Closed-Loop Control State
        self.target_speed = 0.0
        self.decision_state = "NORMAL_DRIVING"
        self.current_path = None
        self.travel_time = 0.0
        self.path_length = 0.0
        self.goal_reached = False
        self.braking_state = "CRUISING"
        self.lookahead_point = (x, y)

    def update(self, dt: float, throttle: float, steering: float):
        """
        Kinematic Bicycle Model update step.
        :param dt: delta time in seconds
        :param throttle: command [-1.0 (max brake) to +1.0 (max throttle)]
        :param steering: command [-1.0 (max left) to +1.0 (max right)]
        """
        self.travel_time += dt
        # Map control inputs
        if throttle >= 0.0:
            self.acceleration = throttle * EGO_MAX_ACCEL
        else:
            self.acceleration = throttle * EGO_MAX_BRAKE  # Negative accel for braking

        self.steering_angle = np.clip(steering * EGO_MAX_STEER, -EGO_MAX_STEER, EGO_MAX_STEER)

        # Update velocity with limits
        self.velocity += self.acceleration * dt
        self.velocity = np.clip(self.velocity, EGO_MIN_SPEED, EGO_MAX_SPEED)

        # Kinematic vehicle state transition
        # Distance moved in dt
        ds = self.velocity * dt
        self.path_length += float(ds)

        if abs(self.steering_angle) > 0.001:
            # Turning radius R = L / tan(steer)
            turning_radius = self.length / math.tan(self.steering_angle)
            d_heading = ds / turning_radius
            self.x += turning_radius * (math.sin(self.heading + d_heading) - math.sin(self.heading))
            self.y -= turning_radius * (math.cos(self.heading + d_heading) - math.cos(self.heading))
            self.heading += d_heading
        else:
            # Straight line motion
            self.x += ds * math.cos(self.heading)
            self.y += ds * math.sin(self.heading)

        # Normalize heading to [-pi, pi]
        self.heading = (self.heading + math.pi) % (2 * math.pi) - math.pi

    def get_corners(self):
        """Returns 4 corner vertices (x, y) of oriented bounding box in world meters."""
        half_l = self.length / 2.0
        half_w = self.width / 2.0
        cos_h = math.cos(self.heading)
        sin_h = math.sin(self.heading)

        rel_corners = [
            (half_l, half_w),
            (half_l, -half_w),
            (-half_l, -half_w),
            (-half_l, half_w)
        ]

        world_corners = []
        for rx, ry in rel_corners:
            wx = self.x + (rx * cos_h - ry * sin_h)
            wy = self.y + (rx * sin_h + ry * cos_h)
            world_corners.append((wx, wy))

        return world_corners

    def follow_waypoint(self, target_x: float, target_y: float, dt: float, target_speed: float = 8.0) -> Tuple[float, float]:
        """
        Simple waypoint following controller (Phase 3).
        Calculates throttle and steering input to drive toward (target_x, target_y).
        Returns (throttle_command, steering_command).
        """
        dx = target_x - self.x
        dy = target_y - self.y
        target_heading = math.atan2(dy, dx)

        heading_error = target_heading - self.heading
        # Normalize heading error to [-pi, pi]
        heading_error = (heading_error + math.pi) % (2 * math.pi) - math.pi

        # Proportional steering control
        steering = float(np.clip(heading_error * 1.5, -1.0, 1.0))

        # Proportional throttle control
        speed_error = target_speed - self.velocity
        throttle = float(np.clip(speed_error * 0.3, -1.0, 1.0))

        # Apply update step
        self.update(dt, throttle, steering)
        return throttle, steering



class Road:
    """
    Represents unstructured Indian road segment boundaries and drivable region.
    """
    def __init__(self, length: float, width: float):
        self.length = length
        self.width = width
        # Lateral boundaries: y in [-width/2, +width/2]
        self.y_min = -width / 2.0
        self.y_max = width / 2.0

    def is_within_road(self, x: float, y: float, margin: float = 0.0) -> bool:
        """Checks if coordinate (x, y) is inside drivable road width."""
        return (self.y_min - margin) <= y <= (self.y_max + margin)
