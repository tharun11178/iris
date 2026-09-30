"""
IRIS Vehicle Safety Checker & Road Boundary Enforcement Engine.
Performs full vehicle footprint polygon verification, road envelope containment,
hazard collision checks, and vehicle condition monitoring.
"""

import math
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import numpy as np

# Road envelope margin from boundary in meters
ROAD_MARGIN = 0.5
SAFE_CLEARANCE_THRESHOLD = 1.0
CAUTION_CLEARANCE_THRESHOLD = 1.8
TTC_CRITICAL_THRESHOLD = 1.5
TTC_WARNING_THRESHOLD = 3.0


class VehicleCondition(Enum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    SLOW_DOWN = "SLOW_DOWN"
    NEAR_COLLISION = "NEAR_COLLISION"
    COLLISION_RISK = "COLLISION_RISK"
    OFF_ROAD = "OFF_ROAD"
    SAFETY_HOLD = "SAFETY_HOLD"
    GOAL_REACHED = "GOAL_REACHED"


@dataclass
class FootprintCheckResult:
    is_safe: bool
    inside_road: bool
    inside_safe_corridor: bool
    collision_detected: bool
    surface_hazard_overlap: bool
    min_obstacle_clearance: float
    min_road_clearance: float
    left_road_clearance: float
    right_road_clearance: float
    violating_corners: List[Tuple[float, float]]
    condition: VehicleCondition
    rejection_reason: str = ""


class VehicleSafetyChecker:
    """
    Validates complete vehicle footprint against road boundaries, safe envelopes,
    and obstacles in simulation coordinates (y=0 road center, y in [-width/2, +width/2]).
    """

    def __init__(
        self,
        road_width: float = 12.0,
        road_length: float = 300.0,
        road_margin: float = ROAD_MARGIN,
        vehicle_length: float = 4.6,
        vehicle_width: float = 2.0,
    ):
        self.road_width = road_width
        self.road_length = road_length
        self.road_margin = road_margin
        self.vehicle_length = vehicle_length
        self.vehicle_width = vehicle_width

        # Physical road lateral limits
        self.y_min = -road_width / 2.0
        self.y_max = road_width / 2.0

        # Safe Corridor Lateral Limits (Road boundary minus margin)
        self.safe_y_min = self.y_min + self.road_margin
        self.safe_y_max = self.y_max - self.road_margin

    def get_vehicle_footprint(
        self,
        x: float,
        y: float,
        heading: float,
        length: Optional[float] = None,
        width: Optional[float] = None,
    ) -> List[Tuple[float, float]]:
        """
        Calculates 4 corner vertices of oriented bounding box in world/sim meters.
        Corners: [Front-Left, Front-Right, Rear-Right, Rear-Left]
        """
        l = length if length is not None else self.vehicle_length
        w = width if width is not None else self.vehicle_width
        half_l = l / 2.0
        half_w = w / 2.0

        cos_h = math.cos(heading)
        sin_h = math.sin(heading)

        rel_corners = [
            (half_l, half_w),    # Front-Left
            (half_l, -half_w),   # Front-Right
            (-half_l, -half_w),  # Rear-Right
            (-half_l, half_w),   # Rear-Left
        ]

        corners = []
        for rx, ry in rel_corners:
            wx = x + (rx * cos_h - ry * sin_h)
            wy = y + (rx * sin_h + ry * cos_h)
            corners.append((wx, wy))

        return corners

    def check_road_boundary(
        self,
        footprint: List[Tuple[float, float]],
        margin: float = 0.0,
    ) -> Tuple[bool, List[Tuple[float, float]]]:
        """
        Checks if all vertices of footprint remain within road lateral bounds [y_min - margin, y_max + margin].
        Returns (is_inside, list_of_violating_corners).
        """
        violating = []
        eff_min = self.y_min - margin
        eff_max = self.y_max + margin

        for cx, cy in footprint:
            if cy < eff_min or cy > eff_max:
                violating.append((cx, cy))

        return len(violating) == 0, violating

    def get_road_offset(self, x: float, y: float) -> float:
        """
        Returns lateral deviation from road centerline (y=0).
        """
        return float(y)

    def get_clearance(
        self,
        footprint: List[Tuple[float, float]],
        traffic_actors: Optional[List[Any]] = None,
    ) -> Tuple[float, float, float, float]:
        """
        Computes (left_road_clearance, right_road_clearance, min_road_clearance, min_obstacle_clearance).
        """
        y_coords = [cy for _, cy in footprint]
        max_y = max(y_coords)
        min_y = min(y_coords)

        # Left road boundary is at +y_max, right road boundary is at -y_min
        left_clearance = max(0.0, self.y_max - max_y)
        right_clearance = max(0.0, min_y - self.y_min)
        min_road_clearance = min(left_clearance, right_clearance)

        # Obstacle clearance
        min_obstacle_clearance = 999.0
        if traffic_actors:
            # Vehicle center
            vx = sum(p[0] for p in footprint) / 4.0
            vy = sum(p[1] for p in footprint) / 4.0

            for actor in traffic_actors:
                ax = getattr(actor, "x", 0.0)
                ay = getattr(actor, "y", 0.0)
                al = getattr(actor, "length", 2.0)
                aw = getattr(actor, "width", 1.0)

                dist = math.hypot(ax - vx, ay - vy) - (self.vehicle_length + al) / 2.0
                if dist < min_obstacle_clearance:
                    min_obstacle_clearance = max(0.0, dist)

        return left_clearance, right_clearance, min_road_clearance, min_obstacle_clearance

    def check_collision(
        self,
        footprint: List[Tuple[float, float]],
        traffic_actors: Optional[List[Any]] = None,
    ) -> Tuple[bool, Optional[Any]]:
        """
        Checks if the vehicle footprint polygon intersects with any traffic actor's bounding box.
        """
        if not traffic_actors:
            return False, None

        vx_coords = [p[0] for p in footprint]
        vy_coords = [p[1] for p in footprint]
        ego_min_x, ego_max_x = min(vx_coords), max(vx_coords)
        ego_min_y, ego_max_y = min(vy_coords), max(vy_coords)

        for actor in traffic_actors:
            ax = getattr(actor, "x", 0.0)
            ay = getattr(actor, "y", 0.0)
            al = getattr(actor, "length", 2.0)
            aw = getattr(actor, "width", 1.0)
            half_al = al / 2.0
            half_aw = aw / 2.0

            act_min_x = ax - half_al
            act_max_x = ax + half_al
            act_min_y = ay - half_aw
            act_max_y = ay + half_aw

            # AABB overlap test
            if not (ego_max_x < act_min_x or ego_min_x > act_max_x or ego_max_y < act_min_y or ego_min_y > act_max_y):
                return True, actor

        return False, None

    def check_surface_hazards(
        self,
        footprint: List[Tuple[float, float]],
        surface_hazards: Optional[List[Any]] = None,
    ) -> Tuple[bool, Optional[Any]]:
        """
        Checks if vehicle footprint overlaps with severe non-traversable surface hazards.
        """
        if not surface_hazards:
            return False, None

        vx_coords = [p[0] for p in footprint]
        vy_coords = [p[1] for p in footprint]
        ego_min_x, ego_max_x = min(vx_coords), max(vx_coords)
        ego_min_y, ego_max_y = min(vy_coords), max(vy_coords)

        for hazard in surface_hazards:
            # Check if hazard is severe non-traversable
            severity = getattr(hazard, "severity", 0.5)
            if severity < 0.7:
                continue

            hx = getattr(hazard, "x", 0.0)
            hy = getattr(hazard, "y", 0.0)
            hl = getattr(hazard, "length", 2.0)
            hw = getattr(hazard, "width", 2.0)

            haz_min_x = hx - hl / 2.0
            haz_max_x = hx + hl / 2.0
            haz_min_y = hy - hw / 2.0
            haz_max_y = hy + hw / 2.0

            if not (ego_max_x < haz_min_x or ego_min_x > haz_max_x or ego_max_y < haz_min_y or ego_min_y > haz_max_y):
                return True, hazard

        return False, None

    def is_footprint_safe(
        self,
        footprint: List[Tuple[float, float]],
        traffic_actors: Optional[List[Any]] = None,
        surface_hazards: Optional[List[Any]] = None,
        ttc: float = 999.0,
        future_risk: float = 0.0,
        speed: float = 0.0,
    ) -> FootprintCheckResult:
        """
        Comprehensive check of the vehicle footprint.
        """
        # 1. Road Boundary Containment
        inside_road, violating_corners = self.check_road_boundary(footprint, margin=0.0)
        inside_corridor, _ = self.check_road_boundary(footprint, margin=-self.road_margin)

        # 2. Clearance
        left_clr, right_clr, min_road_clr, min_obs_clr = self.get_clearance(footprint, traffic_actors)

        # 3. Collision Check
        collision, col_actor = self.check_collision(footprint, traffic_actors)

        # 4. Surface Hazard Overlap
        hazard_overlap, h_obj = self.check_surface_hazards(footprint, surface_hazards)

        # 5. Evaluate VehicleCondition
        condition = VehicleCondition.NORMAL
        rejection_reason = ""
        is_safe = True

        if not inside_road:
            condition = VehicleCondition.OFF_ROAD
            rejection_reason = "FOOTPRINT_OUTSIDE_ROAD_BOUNDARY"
            is_safe = False
        elif collision:
            condition = VehicleCondition.NEAR_COLLISION
            rejection_reason = "OBSTACLE_COLLISION"
            is_safe = False
        elif min_obs_clr < 0.5 or ttc < TTC_CRITICAL_THRESHOLD:
            condition = VehicleCondition.COLLISION_RISK
            rejection_reason = "HIGH_COLLISION_RISK"
            is_safe = False
        elif not inside_corridor or min_road_clr < self.road_margin or min_obs_clr < SAFE_CLEARANCE_THRESHOLD:
            condition = VehicleCondition.CAUTION
            if future_risk > 0.6 or min_obs_clr < 1.2:
                condition = VehicleCondition.SLOW_DOWN
        elif future_risk > 0.5 or ttc < TTC_WARNING_THRESHOLD:
            condition = VehicleCondition.SLOW_DOWN

        return FootprintCheckResult(
            is_safe=is_safe,
            inside_road=inside_road,
            inside_safe_corridor=inside_corridor,
            collision_detected=collision,
            surface_hazard_overlap=hazard_overlap,
            min_obstacle_clearance=min_obs_clr,
            min_road_clearance=min_road_clr,
            left_road_clearance=left_clr,
            right_road_clearance=right_clr,
            violating_corners=violating_corners,
            condition=condition,
            rejection_reason=rejection_reason,
        )

    def is_pose_safe(
        self,
        x: float,
        y: float,
        heading: float,
        traffic_actors: Optional[List[Any]] = None,
        surface_hazards: Optional[List[Any]] = None,
    ) -> bool:
        """
        Convenience wrapper returning boolean whether a candidate (x, y, heading) pose is safe.
        """
        footprint = self.get_vehicle_footprint(x, y, heading)
        result = self.is_footprint_safe(footprint, traffic_actors, surface_hazards)
        return result.is_safe
