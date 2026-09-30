"""
IRIS Surface Risk Calculator (Phase 4)
Calculates spatial surface risk for static road features (potholes, waterlogged sections,
speed breakers, uneven terrain, debris) weighted by severity and confidence.
"""

import math
import numpy as np
from typing import List, Dict, Any
from world.world_model import WorldModel
from world.cell import CellState


class SurfaceRiskModel:
    """
    Computes road surface hazard spatial risk.
    """

    def compute(self, world_model: WorldModel, surface_matrix: np.ndarray):
        """
        Populates surface_matrix in-place with road surface risk values.
        Queries Phase 5 SurfaceModel for detailed hazard severity, confidence, and influence fields.
        """
        surface_matrix.fill(0.0)
        grid = world_model.grid
        surf_model = getattr(world_model, "surface_model", None)

        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                cell = grid.cells[r][c]
                if surf_model is not None and surf_model.get_hazards():
                    surface_matrix[r, c] = surf_model.get_surface_risk(cell.x_world, cell.y_world)
                else:
                    state = cell.state
                    if state == CellState.POTHOLE:
                        surface_matrix[r, c] = max(surface_matrix[r, c], cell.severity * cell.confidence)
                    elif state == CellState.WATER:
                        surface_matrix[r, c] = max(surface_matrix[r, c], cell.severity * cell.confidence * 0.95)
                    elif state == CellState.UNEVEN_TERRAIN:
                        surface_matrix[r, c] = max(surface_matrix[r, c], cell.severity * 0.6)
                    elif state == CellState.RAISED:
                        surface_matrix[r, c] = max(surface_matrix[r, c], cell.severity * 0.5)

        # Smooth spatial margin around hazards (1-cell neighbor blur)
        smoothed = surface_matrix.copy()
        for r in range(1, grid.num_rows - 1):
            for c in range(1, grid.num_cols - 1):
                if surface_matrix[r, c] == 0.0:
                    max_nbr = max(
                        surface_matrix[r-1, c], surface_matrix[r+1, c],
                        surface_matrix[r, c-1], surface_matrix[r, c+1]
                    )
                    if max_nbr > 0.0:
                        smoothed[r, c] = max_nbr * 0.5

        surface_matrix[:] = np.clip(smoothed, 0.0, 1.0)
