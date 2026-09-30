"""
IRIS Path Data Structure (Phase 3)
Encapsulates discrete grid paths, continuous world waypoints, path length,
validity flags, and simple waypoint tracking functionality.
"""

import math
from typing import List, Tuple, Optional


class Path:
    """
    Represents a planned trajectory as discrete grid cells and continuous world waypoints.
    """

    def __init__(
        self,
        grid_points: Optional[List[Tuple[int, int]]] = None,
        world_points: Optional[List[Tuple[float, float]]] = None,
        length: float = 0.0,
        valid: bool = False,
        success: bool = False,
        status_message: str = "INITIALIZED",
    ):
        self.grid_points: List[Tuple[int, int]] = grid_points if grid_points is not None else []
        self.world_points: List[Tuple[float, float]] = world_points if world_points is not None else []
        self.length: float = length
        self.valid: bool = valid
        self.success: bool = success
        self.status_message: str = status_message
        self.current_waypoint_idx: int = 0

    def compute_length(self) -> float:
        """
        Calculates cumulative path distance in world meters.
        """
        if len(self.world_points) < 2:
            self.length = 0.0
            return 0.0

        total_dist = 0.0
        for i in range(len(self.world_points) - 1):
            x1, y1 = self.world_points[i]
            x2, y2 = self.world_points[i + 1]
            total_dist += math.hypot(x2 - x1, y2 - y1)

        self.length = total_dist
        return total_dist

    def get_current_waypoint(self, ego_x: float, ego_y: float, reach_dist: float = 2.5) -> Optional[Tuple[float, float]]:
        """
        Returns the next active target waypoint (x, y) for simple path following.
        Advances current_waypoint_idx when ego gets within reach_dist of active waypoint.
        """
        if not self.success or not self.world_points:
            return None

        # Advance index if close enough to current waypoint
        while self.current_waypoint_idx < len(self.world_points) - 1:
            wx, wy = self.world_points[self.current_waypoint_idx]
            dist = math.hypot(wx - ego_x, wy - ego_y)
            if dist < reach_dist:
                self.current_waypoint_idx += 1
            else:
                break

        return self.world_points[self.current_waypoint_idx]

    def is_goal_reached(self, ego_x: float, ego_y: float, goal_threshold: float = 3.0) -> bool:
        """
        Returns True if ego vehicle is within goal_threshold meters of the final waypoint.
        """
        if not self.world_points:
            return False
        goal_x, goal_y = self.world_points[-1]
        return math.hypot(goal_x - ego_x, goal_y - ego_y) <= goal_threshold
