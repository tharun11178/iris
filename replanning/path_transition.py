"""
IRIS Path Transition Manager (Phase 12).
Handles smooth, continuous geometric transitions between old and newly selected paths,
ensuring the new route originates smoothly from the current ego position without
teleportation, backward movement, or sudden discontinuities.
"""

import math
from typing import List, Tuple, Optional
from world.world_model import WorldModel
from planning.path import Path


class PathTransitionManager:
    """
    Manages smooth geometric path transitions between old and new route candidates.
    """

    def create_transition_path(
        self,
        ego_pos: Tuple[float, float],
        new_path: Path,
        world_model: WorldModel,
    ) -> Path:
        """
        Constructs a continuous transition path starting at ego_pos and merging seamlessly
        into new_path waypoints.
        """
        if new_path is None or not new_path.world_points:
            return new_path

        ego_x, ego_y = ego_pos
        world_pts = list(new_path.world_points)
        converter = world_model.converter

        # Find closest waypoint on new_path to current ego position
        closest_idx = 0
        min_dist = 9999.0
        for i, (wx, wy) in enumerate(world_pts):
            d = math.hypot(wx - ego_x, wy - ego_y)
            if d < min_dist:
                min_dist = d
                closest_idx = i

        # If start point of new path is already close to ego (e.g. < 1.0m), use ego as first point
        if min_dist < 1.0:
            world_pts[0] = (ego_x, ego_y)
            merged_pts = world_pts
        else:
            # Connect ego_pos to the closest forward waypoint on new_path
            target_idx = min(len(world_pts) - 1, closest_idx + 1)
            target_pt = world_pts[target_idx]

            # Generate linear/bezier interpolation bridge from ego_pos to target_pt
            dist_bridge = math.hypot(target_pt[0] - ego_x, target_pt[1] - ego_y)
            num_steps = max(2, int(math.ceil(dist_bridge / 0.5)))

            bridge_pts = []
            for s in range(num_steps):
                alpha = s / float(num_steps)
                bx = ego_x + alpha * (target_pt[0] - ego_x)
                by = ego_y + alpha * (target_pt[1] - ego_y)
                bridge_pts.append((bx, by))

            merged_pts = bridge_pts + world_pts[target_idx:]

        # Re-grid conversion
        grid_pts = [converter.world_to_grid(wx, wy) for wx, wy in merged_pts]

        transition_path = Path(
            grid_points=grid_pts,
            world_points=merged_pts,
            valid=True,
            success=True,
            status_message=f"Transitioned ({new_path.status_message})",
        )
        transition_path.compute_length()
        return transition_path
