"""
IRIS Evaluation Metrics Engine (Combined Phase 15).
Calculates quantitative metrics for safety, efficiency, path smoothness, replanning, and risk.
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class CollisionRecord:
    """Record of a collision event."""
    timestamp: float
    actor_id: int
    actor_type: str
    ego_x: float
    ego_y: float
    actor_x: float
    actor_y: float
    relative_velocity: float


@dataclass
class SmoothnessMetrics:
    """Path smoothness statistics."""
    total_heading_change: float = 0.0
    mean_curvature: float = 0.0
    max_curvature: float = 0.0
    curvature_variance: float = 0.0
    mean_curvature_rate: float = 0.0
    smoothness_score: float = 1.0  # 1.0 = perfectly smooth, 0.0 = highly erratic


class MetricsCalculator:
    """
    Core numerical metrics calculator for autonomous driving evaluation.
    """

    def __init__(self, near_collision_threshold: float = 1.2):
        self.near_collision_threshold = near_collision_threshold

    def calculate_ttc(self, ego_x: float, ego_y: float, ego_vx: float, ego_vy: float,
                      actor_x: float, actor_y: float, actor_vx: float, actor_vy: float,
                      ego_radius: float = 2.0, actor_radius: float = 1.5) -> float:
        """
        Calculate Time-To-Collision (TTC) between ego and actor.
        Returns float in seconds, or float('inf') if no collision path.
        """
        dx = actor_x - ego_x
        dy = actor_y - ego_y
        dist = math.hypot(dx, dy) - (ego_radius + actor_radius)
        if dist <= 0.0:
            return 0.0

        dvx = ego_vx - actor_vx
        dvy = ego_vy - actor_vy

        # Relative speed along closing vector
        closing_speed = (dx * dvx + dy * dvy) / max(0.001, math.hypot(dx, dy))
        if closing_speed <= 0.0:
            return float('inf')

        return max(0.0, dist / closing_speed)

    def calculate_path_smoothness(self, path: List[Tuple[float, float]]) -> SmoothnessMetrics:
        """
        Calculate explainable path smoothness metrics based on heading changes and curvature.
        """
        if len(path) < 3:
            return SmoothnessMetrics()

        pts = np.array(path)
        dx = np.diff(pts[:, 0])
        dy = np.diff(pts[:, 1])

        headings = np.arctan2(dy, dx)
        heading_diffs = np.abs(np.diff(headings))
        # Wrap heading diffs to [0, pi]
        heading_diffs = np.where(heading_diffs > np.pi, 2 * np.pi - heading_diffs, heading_diffs)
        total_heading_change = float(np.sum(heading_diffs))

        # Calculate discrete curvature k = |x'y'' - y'x''| / (x'^2 + y'^2)^(3/2)
        ds = np.hypot(dx[:-1], dy[:-1])
        ds = np.where(ds < 1e-4, 1e-4, ds)

        d_heading = np.diff(headings)
        d_heading = np.where(d_heading > np.pi, d_heading - 2 * np.pi, d_heading)
        d_heading = np.where(d_heading < -np.pi, d_heading + 2 * np.pi, d_heading)

        curvatures = np.abs(d_heading / ds)
        mean_k = float(np.mean(curvatures)) if len(curvatures) > 0 else 0.0
        max_k = float(np.max(curvatures)) if len(curvatures) > 0 else 0.0
        var_k = float(np.var(curvatures)) if len(curvatures) > 0 else 0.0

        curv_rates = np.abs(np.diff(curvatures)) / ds[1:] if len(curvatures) > 1 else np.array([0.0])
        mean_dk = float(np.mean(curv_rates)) if len(curv_rates) > 0 else 0.0

        # Smoothness score: 1.0 - normalized penalty
        penalty = min(1.0, (mean_k * 0.5 + mean_dk * 0.3 + var_k * 0.2))
        smoothness_score = max(0.0, 1.0 - penalty)

        return SmoothnessMetrics(
            total_heading_change=total_heading_change,
            mean_curvature=mean_k,
            max_curvature=max_k,
            curvature_variance=var_k,
            mean_curvature_rate=mean_dk,
            smoothness_score=smoothness_score
        )

    def is_collision(self, ego_x: float, ego_y: float, ego_length: float, ego_width: float,
                     actor_x: float, actor_y: float, actor_length: float, actor_width: float) -> bool:
        """
        Check physical bounding box collision.
        """
        d = math.hypot(ego_x - actor_x, ego_y - actor_y)
        min_safe_dist = (ego_length + actor_length) * 0.35 + (ego_width + actor_width) * 0.35
        return d < min_safe_dist

    def is_near_collision(self, ego_x: float, ego_y: float, actor_x: float, actor_y: float) -> bool:
        """
        Check near collision threshold.
        """
        d = math.hypot(ego_x - actor_x, ego_y - actor_y)
        return d < self.near_collision_threshold
