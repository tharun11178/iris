"""
IRIS Boundary Risk Calculator (Phase 4)
Calculates spatial boundary risk increasing smoothly as cells approach road shoulder edges.
"""

import numpy as np
from world.world_model import WorldModel
from world.cell import CellState
from risk_engine.config import BOUNDARY_INFLUENCE_DIST
from configs.sim_config import ROAD_WIDTH, ROAD_MARGIN


class BoundaryRiskModel:
    """
    Computes road edge & boundary spatial risk.
    """

    def __init__(self, influence_dist: float = BOUNDARY_INFLUENCE_DIST):
        self.influence_dist = influence_dist

    def compute(self, world_model: WorldModel, boundary_matrix: np.ndarray):
        """
        Populates boundary_matrix in-place with road boundary risk values.
        """
        boundary_matrix.fill(0.0)
        grid = world_model.grid

        y_min_road = ROAD_MARGIN                        # e.g., 3.0m
        y_max_road = ROAD_MARGIN + ROAD_WIDTH           # e.g., 15.0m

        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                cell = grid.cells[r][c]
                y_center = cell.y_world

                if cell.state == CellState.OUTSIDE_ROAD:
                    boundary_matrix[r, c] = 1.0
                elif cell.state == CellState.ROAD_BOUNDARY:
                    boundary_matrix[r, c] = 0.85
                else:
                    # Distance to closest road boundary edge
                    dist_to_min = y_center - y_min_road
                    dist_to_max = y_max_road - y_center
                    min_edge_dist = min(dist_to_min, dist_to_max)

                    if min_edge_dist < self.influence_dist:
                        # Smooth boundary risk decay from edge
                        risk_factor = max(0.0, 1.0 - (min_edge_dist / self.influence_dist))
                        boundary_matrix[r, c] = risk_factor * 0.70

        np.clip(boundary_matrix, 0.0, 1.0, out=boundary_matrix)
