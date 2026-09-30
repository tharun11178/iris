"""
IRIS Candidate Generator (Phase 11).
Generates multiple diverse candidate paths / corridors connecting start and goal positions
across available negative-space regions.
"""

import math
from typing import List, Tuple, Optional, Any
from planning.astar import AStarPlanner
from planning.path import Path
from world.world_model import WorldModel
from safe_space.corridor import SafeCorridor
from safe_space.config import MAX_CANDIDATES, LOCAL_PLANNING_RADIUS


class CandidateGenerator:
    """
    Generates distinct candidate paths through different spatial corridors.
    """

    def __init__(self, max_candidates: int = MAX_CANDIDATES):
        self.max_candidates = max_candidates
        self.baseline_planner = AStarPlanner(allow_diagonal=False)

    def generate_candidates(
        self,
        start_pos: Tuple[float, float],
        goal_pos: Tuple[float, float],
        world_model: WorldModel,
        clearance_grid: Optional[Any] = None,
    ) -> List[SafeCorridor]:
        """
        Generates up to `max_candidates` distinct candidate routes between start_pos and goal_pos.
        """
        candidates: List[SafeCorridor] = []
        converter = world_model.converter

        # Determine lateral orientation vector for biasing (perpendicular to start-goal vector)
        dx = goal_pos[0] - start_pos[0]
        dy = goal_pos[1] - start_pos[1]
        dist_goal = math.hypot(dx, dy)
        if dist_goal < 1e-3:
            dist_goal = 1.0

        # Normal vector pointing left (+90 deg)
        nx = -dy / dist_goal
        ny = dx / dist_goal

        # Candidate configurations: (name, lateral_offset_mid, lateral_offset_goal)
        configs = [
            ("CENTER_CORRIDOR", 0.0, 0.0),
            ("LEFT_CORRIDOR", 2.5, 1.5),
            ("RIGHT_CORRIDOR", -2.5, -1.5),
            ("WIDE_LEFT_CORRIDOR", 4.5, 3.0),
            ("WIDE_RIGHT_CORRIDOR", -4.5, -3.0),
        ]

        candidate_id_cnt = 1

        for name, mid_offset, goal_offset in configs:
            if len(candidates) >= self.max_candidates:
                break

            # Intermediate waypoint at 50% distance to goal
            mid_x = start_pos[0] + 0.5 * dx + mid_offset * nx
            mid_y = start_pos[1] + 0.5 * dy + mid_offset * ny

            biased_goal_x = goal_pos[0] + goal_offset * nx
            biased_goal_y = goal_pos[1] + goal_offset * ny

            # Check bounds and drivability of biased targets
            bg_r, bg_c = converter.world_to_grid(biased_goal_x, biased_goal_y)
            if not (0 <= bg_r < world_model.grid.num_rows and 0 <= bg_c < world_model.grid.num_cols):
                biased_goal_x, biased_goal_y = goal_pos[0], goal_pos[1]

            # Generate candidate path segment using baseline A* search
            if abs(mid_offset) < 0.1:
                # Direct route
                planned_path = self.baseline_planner.plan(start_pos, (biased_goal_x, biased_goal_y), world_model)
            else:
                # Route via intermediate waypoints
                path1 = self.baseline_planner.plan(start_pos, (mid_x, mid_y), world_model)
                if path1.success:
                    path2 = self.baseline_planner.plan((mid_x, mid_y), (biased_goal_x, biased_goal_y), world_model)
                    if path2.success:
                        combined_wpt = path1.world_points + path2.world_points[1:]
                        combined_grid = path1.grid_points + path2.grid_points[1:]
                        planned_path = Path(
                            world_points=combined_wpt,
                            grid_points=combined_grid,
                            length=path1.length + path2.length,
                            valid=True,
                            success=True,
                            status_message="Multi-segment Candidate Path",
                        )
                    else:
                        planned_path = path1
                else:
                    planned_path = self.baseline_planner.plan(start_pos, (biased_goal_x, biased_goal_y), world_model)

            if planned_path is not None and planned_path.success and len(planned_path.world_points) > 1:
                # Construct SafeCorridor instance
                corridor = SafeCorridor(
                    corridor_id=f"CORRIDOR_{candidate_id_cnt:02d}",
                    name=name,
                    centerline=list(planned_path.world_points),
                    grid_cells=list(planned_path.grid_points),
                    length=planned_path.length,
                    is_valid=True,
                )
                candidates.append(corridor)
                candidate_id_cnt += 1

        # Fallback: if no candidates generated, create a straight-line fallback corridor
        if not candidates:
            w_pts = [start_pos, goal_pos]
            g_pts = [converter.world_to_grid(start_pos[0], start_pos[1]), converter.world_to_grid(goal_pos[0], goal_pos[1])]
            fallback_corridor = SafeCorridor(
                corridor_id="CORRIDOR_FALLBACK",
                name="FALLBACK_STRAIGHT",
                centerline=w_pts,
                grid_cells=g_pts,
                length=dist_goal,
                is_valid=False,
                rejection_reason="No valid A* candidate path found",
            )
            candidates.append(fallback_corridor)

        return candidates
