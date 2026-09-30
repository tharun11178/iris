"""
IRIS Free Space Region Detector (Phase 11).
Identifies connected components of traversable grid cells (negative space)
and extracts region geometry, clearance, and risk metrics.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set, Optional, Any
import math
import numpy as np

from world.world_model import WorldModel
from world.cell import CellState
from safe_space.config import CONNECTED_NEIGHBORHOOD, MIN_CORRIDOR_WIDTH


@dataclass
class FreeSpaceRegion:
    """
    Represents a contiguous connected component of drivable negative-space cells.
    """
    region_id: int
    cells: List[Tuple[int, int]] = field(default_factory=list)
    area: float = 0.0                      # Total area in square meters
    centroid: Tuple[float, float] = (0.0, 0.0)  # World coordinates (x, y)
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    width: float = 0.0                     # Lateral extent in meters
    length: float = 0.0                    # Longitudinal extent in meters
    min_clearance: float = 0.0             # Minimum distance to nearest obstacle
    avg_clearance: float = 0.0             # Average distance to nearest obstacle
    avg_risk: float = 0.0                  # Average spatial risk within region
    peak_risk: float = 0.0                 # Peak spatial risk within region

    def contains_world_point(self, x_world: float, y_world: float, converter: Any) -> bool:
        """Returns True if the given world coordinate falls inside this region."""
        r, c = converter.world_to_grid(x_world, y_world)
        return (r, c) in self.cells


class FreeSpaceDetector:
    """
    Analyzes occupancy grid to identify connected drivable regions using BFS/DFS component labeling.
    """

    def __init__(self, neighborhood: int = CONNECTED_NEIGHBORHOOD):
        self.neighborhood = neighborhood

    def get_neighbors(self, row: int, col: int, num_rows: int, num_cols: int) -> List[Tuple[int, int]]:
        """Returns 4-connected or 8-connected valid grid neighbors."""
        neighbors = []
        if self.neighborhood == 4:
            dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            dirs = [
                (-1, 0), (1, 0), (0, -1), (0, 1),
                (-1, -1), (-1, 1), (1, -1), (1, 1)
            ]

        for dr, dc in dirs:
            nr, nc = row + dr, col + dc
            if 0 <= nr < num_rows and 0 <= nc < num_cols:
                neighbors.append((nr, nc))
        return neighbors

    def detect_regions(
        self,
        world_model: WorldModel,
        clearance_grid: Optional[np.ndarray] = None,
        risk_matrix: Optional[np.ndarray] = None,
    ) -> List[FreeSpaceRegion]:
        """
        Extracts contiguous connected drivable regions from WorldModel.
        """
        grid = world_model.grid
        converter = world_model.converter
        num_rows = grid.num_rows
        num_cols = grid.num_cols
        res = grid.grid_res

        visited: Set[Tuple[int, int]] = set()
        regions: List[FreeSpaceRegion] = []
        region_counter = 1

        for r in range(num_rows):
            for c in range(num_cols):
                cell = grid.cells[r][c]

                # Region eligibility: Cell must be drivable and not already visited
                if cell.is_drivable and (r, c) not in visited:
                    # Perform BFS to collect all connected cells in this component
                    component_cells: List[Tuple[int, int]] = []
                    queue = [(r, c)]
                    visited.add((r, c))

                    while queue:
                        curr_r, curr_c = queue.pop(0)
                        component_cells.append((curr_r, curr_c))

                        for nr, nc in self.get_neighbors(curr_r, curr_c, num_rows, num_cols):
                            n_cell = grid.cells[nr][nc]
                            if n_cell.is_drivable and (nr, nc) not in visited:
                                visited.add((nr, nc))
                                queue.append((nr, nc))

                    # Calculate region statistics
                    if component_cells:
                        world_pts = [converter.grid_to_world(cr, cc) for cr, cc in component_cells]
                        xs = [pt[0] for pt in world_pts]
                        ys = [pt[1] for pt in world_pts]

                        centroid_x = float(np.mean(xs))
                        centroid_y = float(np.mean(ys))
                        min_x, max_x = min(xs), max(xs)
                        min_y, max_y = min(ys), max(ys)
                        area = len(component_cells) * (res * res)

                        min_clearance = 0.0
                        avg_clearance = 0.0
                        if clearance_grid is not None:
                            clearances = [clearance_grid[cr, cc] for cr, cc in component_cells]
                            min_clearance = float(np.min(clearances)) if clearances else 0.0
                            avg_clearance = float(np.mean(clearances)) if clearances else 0.0

                        avg_risk = 0.0
                        peak_risk = 0.0
                        if risk_matrix is not None:
                            risks = [risk_matrix[cr, cc] for cr, cc in component_cells]
                            avg_risk = float(np.mean(risks)) if risks else 0.0
                            peak_risk = float(np.max(risks)) if risks else 0.0

                        region = FreeSpaceRegion(
                            region_id=region_counter,
                            cells=component_cells,
                            area=area,
                            centroid=(centroid_x, centroid_y),
                            min_x=min_x,
                            max_x=max_x,
                            min_y=min_y,
                            max_y=max_y,
                            width=max_y - min_y,
                            length=max_x - min_x,
                            min_clearance=min_clearance,
                            avg_clearance=avg_clearance,
                            avg_risk=avg_risk,
                            peak_risk=peak_risk,
                        )
                        regions.append(region)
                        region_counter += 1

        # Sort regions by area descending
        regions.sort(key=lambda reg: reg.area, reverse=True)
        return regions
