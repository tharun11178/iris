"""
IRIS A* (A-Star) Grid Path Planner (Phase 3)
Implements 4-connected grid A* shortest path search over the Phase 2 OccupancyGrid.
Returns a validated Path instance containing discrete grid points and continuous world waypoints.
"""

import math
import heapq
from typing import List, Tuple, Dict, Set, Optional
from planning.path import Path
from world.world_model import WorldModel
from world.cell import CellState, GridCell


class AStarPlanner:
    """
    Standard Grid-based A* Pathfinder.
    """

    def __init__(self, allow_diagonal: bool = False):
        self.allow_diagonal = allow_diagonal

        # 4-connected grid directions (Up, Down, Left, Right)
        self.directions = [
            (-1, 0),  # Up
            (1, 0),   # Down
            (0, -1),  # Left
            (0, 1),   # Right
        ]
        if allow_diagonal:
            # 8-connected directions
            self.directions.extend([
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ])

    def heuristic(self, r1: int, c1: int, r2: int, c2: int, res: float) -> float:
        """
        Manhattan distance heuristic estimate to goal in world meters.
        """
        return (abs(r1 - r2) + abs(c1 - c2)) * res

    def _get_clearance_penalty(self, grid, r: int, c: int, margin: int = 2) -> float:
        """
        Calculates clearance penalty to steer paths away from obstacle boundaries.
        """
        penalty = 0.0
        for dr in range(-margin, margin + 1):
            for dc in range(-margin, margin + 1):
                if dr == 0 and dc == 0:
                    continue
                neighbor = grid.get_cell(r + dr, c + dc)
                if neighbor is not None and not neighbor.is_drivable:
                    dist = math.hypot(dr, dc)
                    penalty += (0.5 / dist) * grid.grid_res
        return penalty



    def plan(
        self,
        start_world: Tuple[float, float],
        goal_world: Tuple[float, float],
        world_model: WorldModel,
    ) -> Path:
        """
        Executes A* search from start_world (x, y) to goal_world (x, y).
        """
        grid = world_model.grid
        converter = world_model.converter

        start_x, start_y = start_world
        goal_x, goal_y = goal_world

        # 1. Convert World to Grid Coordinates
        start_r, start_c = converter.world_to_grid(start_x, start_y)
        goal_r, goal_c = converter.world_to_grid(goal_x, goal_y)

        start_cell = grid.get_cell(start_r, start_c)
        goal_cell = grid.get_cell(goal_r, goal_c)

        # 2. Validate Start and Goal Cells
        if start_cell is None or goal_cell is None:
            return Path(success=False, valid=False, status_message="OUT_OF_BOUNDS")

        # Trivial path check: start == goal
        if (start_r, start_c) == (goal_r, goal_c):
            w_pt = converter.grid_to_world(start_r, start_c)
            path = Path(
                grid_points=[(start_r, start_c)],
                world_points=[w_pt],
                length=0.0,
                valid=True,
                success=True,
                status_message="TRIVIAL_PATH_START_EQUALS_GOAL",
            )
            return path

        # Check if Goal cell is drivable
        if not goal_cell.is_drivable:
            # Search for nearest drivable neighbor cell to goal
            goal_r, goal_c, goal_cell = self._find_nearest_drivable(grid, goal_r, goal_c)
            if goal_cell is None:
                return Path(success=False, valid=False, status_message="GOAL_BLOCKED")

        # 3. A* Search Data Structures
        open_set = []
        # Item: (f_score, g_score, (r, c))
        start_h = self.heuristic(start_r, start_c, goal_r, goal_c, grid.grid_res)
        heapq.heappush(open_set, (start_h, 0.0, (start_r, start_c)))

        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {(start_r, start_c): 0.0}
        closed_set: Set[Tuple[int, int]] = set()

        found = False

        # 4. A* Search Loop
        while open_set:
            current_f, current_g, current_node = heapq.heappop(open_set)
            curr_r, curr_c = current_node

            if current_node in closed_set:
                continue
            closed_set.add(current_node)

            if current_node == (goal_r, goal_c):
                found = True
                break

            for dr, dc in self.directions:
                nr, nc = curr_r + dr, curr_c + dc
                neighbor_node = (nr, nc)

                if neighbor_node in closed_set:
                    continue

                cell = grid.get_cell(nr, nc)
                if cell is None or (not cell.is_drivable and cell.state != CellState.VEHICLE):
                    continue


                # Step movement cost (straight = res, diagonal = sqrt(2)*res)
                step_dist = grid.grid_res if (dr == 0 or dc == 0) else grid.grid_res * math.sqrt(2)
                
                # Apply speed penalty factor if surface is restricted (e.g. speed breaker)
                penalty_mult = 1.0 / max(0.1, world_model.evaluator.get_speed_penalty(cell))
                
                # Add obstacle clearance penalty to steer path away from obstacle borders
                clearance_penalty = self._get_clearance_penalty(grid, nr, nc)
                tentative_g = current_g + (step_dist * penalty_mult) + clearance_penalty

                if neighbor_node not in g_score or tentative_g < g_score[neighbor_node]:
                    came_from[neighbor_node] = current_node
                    g_score[neighbor_node] = tentative_g
                    h_val = self.heuristic(nr, nc, goal_r, goal_c, grid.grid_res)
                    f_val = tentative_g + h_val
                    heapq.heappush(open_set, (f_val, tentative_g, neighbor_node))

        # 5. Path Reconstruction
        if not found:
            return Path(success=False, valid=False, status_message="NO_SAFE_PATH_FOUND")

        grid_path = []
        curr = (goal_r, goal_c)
        while curr in came_from:
            grid_path.append(curr)
            curr = came_from[curr]
        grid_path.append((start_r, start_c))
        grid_path.reverse()

        # Convert Grid Points to World Waypoints
        world_path = [converter.grid_to_world(r, c) for r, c in grid_path]

        path = Path(
            grid_points=grid_path,
            world_points=world_path,
            valid=True,
            success=True,
            status_message="PATH_FOUND",
        )
        path.compute_length()
        return path

    def _find_nearest_drivable(self, grid, r: int, c: int, max_radius: int = 5) -> Tuple[int, int, Optional[GridCell]]:
        """
        Finds the closest drivable cell to (r, c) within max_radius search ring.
        """
        for rad in range(1, max_radius + 1):
            for dr in range(-rad, rad + 1):
                for dc in range(-rad, rad + 1):
                    nr, nc = r + dr, c + dc
                    cell = grid.get_cell(nr, nc)
                    if cell is not None and cell.is_drivable:
                        return nr, nc, cell
        return r, c, None
