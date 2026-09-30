"""
IRIS Collision Risk Calculator (Phase 4)
Calculates current spatial collision proximity risk.
Occupied cells receive 1.0 collision risk; surrounding cells decay smoothly with distance.
"""

import math
import numpy as np
from world.world_model import WorldModel
from world.cell import CellState
from risk_engine.config import COLLISION_INFLUENCE_RADIUS


class CollisionRiskModel:
    """
    Computes spatial collision proximity risk.
    """

    def __init__(self, radius: float = COLLISION_INFLUENCE_RADIUS):
        self.radius = radius

    def compute(self, world_model: WorldModel, collision_matrix: np.ndarray):
        """
        Populates collision_matrix in-place with spatial collision proximity risk values.
        """
        collision_matrix.fill(0.0)
        grid = world_model.grid
        res = grid.grid_res

        rad_cells = int(math.ceil(self.radius / res))

        occupied_coords = []
        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                cell = grid.cells[r][c]
                if cell.state in (CellState.OCCUPIED, CellState.VEHICLE, CellState.DYNAMIC_OBJECT):
                    collision_matrix[r, c] = 1.0
                    occupied_coords.append((r, c, cell.x_world, cell.y_world))

        # Spatial decay around occupied cells
        for r_occ, c_occ, ox, oy in occupied_coords:
            r_min = max(0, r_occ - rad_cells)
            r_max = min(grid.num_rows - 1, r_occ + rad_cells)
            c_min = max(0, c_occ - rad_cells)
            c_max = min(grid.num_cols - 1, c_occ + rad_cells)

            for r in range(r_min, r_max + 1):
                for c in range(c_min, c_max + 1):
                    cell = grid.cells[r][c]
                    dist = math.hypot(cell.x_world - ox, cell.y_world - oy)
                    if dist <= self.radius:
                        spatial_risk = max(0.0, 1.0 - (dist / self.radius))
                        collision_matrix[r, c] = max(collision_matrix[r, c], spatial_risk * 0.90)

        np.clip(collision_matrix, 0.0, 1.0, out=collision_matrix)
