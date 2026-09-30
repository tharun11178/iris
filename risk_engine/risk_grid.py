"""
IRIS Risk Grid Representation (Phase 4)
Maintains discrete 2D floating-point matrices for individual risk components
and normalized total spatial risk over the WorldModel grid.
"""

import numpy as np
from typing import Tuple, Dict


class RiskGrid:
    """
    2D Matrix representing continuous spatial risk values across the environment.
    All risk values are normalized and clamped to [0.0, 1.0].
    """

    def __init__(self, num_rows: int, num_cols: int, grid_res: float = 0.5):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.grid_res = grid_res

        # Component matrices initialized to zero
        self.traffic_risk = np.zeros((num_rows, num_cols), dtype=np.float64)
        self.surface_risk = np.zeros((num_rows, num_cols), dtype=np.float64)
        self.boundary_risk = np.zeros((num_rows, num_cols), dtype=np.float64)
        self.collision_risk = np.zeros((num_rows, num_cols), dtype=np.float64)
        self.total_risk = np.zeros((num_rows, num_cols), dtype=np.float64)

    def clear(self):
        """
        Resets all component risk matrices to zero.
        """
        self.traffic_risk.fill(0.0)
        self.surface_risk.fill(0.0)
        self.boundary_risk.fill(0.0)
        self.collision_risk.fill(0.0)
        self.total_risk.fill(0.0)

    def get_risk(self, row: int, col: int) -> float:
        """
        Returns normalized total risk at grid coordinate (row, col).
        """
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return float(self.total_risk[row, col])
        return 1.0  # Out of bounds treated as max risk

    def get_component_risk(self, row: int, col: int) -> Dict[str, float]:
        """
        Returns component breakdown dictionary for grid cell (row, col).
        """
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return {
                "traffic": float(self.traffic_risk[row, col]),
                "surface": float(self.surface_risk[row, col]),
                "boundary": float(self.boundary_risk[row, col]),
                "collision": float(self.collision_risk[row, col]),
                "total": float(self.total_risk[row, col]),
            }
        return {"traffic": 1.0, "surface": 1.0, "boundary": 1.0, "collision": 1.0, "total": 1.0}

    def set_risk(self, row: int, col: int, value: float):
        """
        Sets total risk value for a specific cell, clamped to [0.0, 1.0].
        """
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            self.total_risk[row, col] = np.clip(value, 0.0, 1.0)

    def normalize(self):
        """
        Clamps all risk matrices strictly to [0.0, 1.0].
        """
        np.clip(self.traffic_risk, 0.0, 1.0, out=self.traffic_risk)
        np.clip(self.surface_risk, 0.0, 1.0, out=self.surface_risk)
        np.clip(self.boundary_risk, 0.0, 1.0, out=self.boundary_risk)
        np.clip(self.collision_risk, 0.0, 1.0, out=self.collision_risk)
        np.clip(self.total_risk, 0.0, 1.0, out=self.total_risk)

    def get_max_risk(self) -> float:
        """
        Returns maximum total risk value in the grid.
        """
        return float(np.max(self.total_risk))

    def get_average_risk(self) -> float:
        """
        Returns mean total risk value across all grid cells.
        """
        return float(np.mean(self.total_risk))
