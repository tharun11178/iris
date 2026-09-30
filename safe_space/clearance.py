"""
IRIS Clearance Map Model (Phase 11).
Computes a 2D spatial distance transform mapping each grid cell to its Euclidean clearance distance (in meters)
from the nearest non-traversable cell, obstacle, surface hazard, or road boundary.
"""

import math
import numpy as np
from typing import Tuple, Optional, Any
from world.world_model import WorldModel
from world.cell import CellState


class ClearanceMap:
    """
    Computes spatial clearance distance grid for negative space safety analysis.
    """

    def __init__(self):
        self.clearance_grid: Optional[np.ndarray] = None
        self.num_rows: int = 0
        self.num_cols: int = 0
        self.grid_res: float = 0.5

    def compute_clearance(self, world_model: WorldModel) -> np.ndarray:
        """
        Calculates 2D array (num_rows, num_cols) of clearance distance in meters.
        
        Non-traversable cells (OUTSIDE_ROAD, ROAD_BOUNDARY, OCCUPIED, NON_TRAVERSABLE hazards)
        have clearance = 0.0m. Drivable cells have clearance equal to distance to nearest non-traversable cell.
        """
        grid = world_model.grid
        num_rows = grid.num_rows
        num_cols = grid.num_cols
        res = grid.grid_res
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.grid_res = res

        # 1. Create binary obstacle matrix (1 = obstacle/non-traversable, 0 = drivable/free)
        obstacle_mask = np.zeros((num_rows, num_cols), dtype=bool)

        for r in range(num_rows):
            for c in range(num_cols):
                cell = grid.cells[r][c]
                # Non-drivable or occupied cells count as clearance boundaries (excluding ego vehicle footprint CELLState.VEHICLE)
                if cell.state in (CellState.OUTSIDE_ROAD, CellState.ROAD_BOUNDARY, CellState.OCCUPIED, CellState.DYNAMIC_OBJECT):
                    obstacle_mask[r, c] = True
                elif not cell.is_drivable and cell.state != CellState.VEHICLE:
                    obstacle_mask[r, c] = True

        # 2. Fast Grid Euclidean Distance Transform
        # Use scipy distance transform if available, or fallback to grid BFS distance transform
        try:
            from scipy.ndimage import distance_transform_edt
            # distance_transform_edt calculates distance to nearest 0 in inverse mask
            free_mask = ~obstacle_mask
            dist_grid = distance_transform_edt(free_mask) * res
        except ImportError:
            dist_grid = self._grid_bfs_distance_transform(obstacle_mask, num_rows, num_cols, res)

        self.clearance_grid = dist_grid
        return dist_grid

    def _grid_bfs_distance_transform(
        self,
        obstacle_mask: np.ndarray,
        num_rows: int,
        num_cols: int,
        res: float,
    ) -> np.ndarray:
        """
        Grid-based Multi-Source BFS distance transform calculation in Python/NumPy (fallback).
        """
        dist_grid = np.full((num_rows, num_cols), fill_value=999.0, dtype=np.float64)
        queue = []

        # Enqueue all obstacle cells with distance 0.0
        obs_rows, obs_cols = np.where(obstacle_mask)
        for r, c in zip(obs_rows, obs_cols):
            dist_grid[r, c] = 0.0
            queue.append((r, c))

        # BFS expansion
        dirs = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        head = 0

        while head < len(queue):
            r, c = queue[head]
            head += 1
            curr_dist = dist_grid[r, c]

            for dr, dc in dirs:
                nr, nc = r + dr, c + dc
                if 0 <= nr < num_rows and 0 <= nc < num_cols:
                    step_cost = math.hypot(dr, dc) * res
                    new_dist = curr_dist + step_cost
                    if new_dist < dist_grid[nr, nc]:
                        dist_grid[nr, nc] = new_dist
                        queue.append((nr, nc))

        return dist_grid

    def get_clearance_at_world(self, x_world: float, y_world: float, converter: Any) -> float:
        """Returns clearance distance in meters at the specified world coordinate."""
        if self.clearance_grid is None:
            return 0.0
        r, c = converter.world_to_grid(x_world, y_world)
        return float(self.clearance_grid[r, c])
