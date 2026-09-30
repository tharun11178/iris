"""
IRIS Uncertainty Risk Expansion Model (Phase 10).
Applies Phase 9 uncertainty spatial expansion to predicted trajectory risk footprints.
Differentiates prediction confidence (scales peak risk height) from prediction uncertainty (expands spatial spread).
"""

import math
import numpy as np
from typing import Optional, Any
from uncertainty.uncertainty_model import UncertaintySet
from future_risk.config import UNCERTAINTY_SPREAD_SCALE, MAX_UNCERTAINTY


class UncertaintyRiskModel:
    """
    Expands spatial risk footprint based on Phase 9 spatio-temporal uncertainty values.
    """

    def __init__(self, spread_scale: float = UNCERTAINTY_SPREAD_SCALE):
        self.spread_scale = spread_scale

    def calculate_expanded_radius(self, base_radius: float, uncertainty_score: float) -> float:
        """
        Calculates expanded spatial risk radius based on uncertainty score [0.0, 1.0].
        LOW uncertainty -> tight base radius.
        HIGH uncertainty -> expanded radius: R_exp = R_base * (1.0 + spread_scale * u).
        """
        u_clamped = max(0.0, min(1.0, uncertainty_score))
        return base_radius * (1.0 + self.spread_scale * u_clamped)

    def apply_uncertainty_expansion(
        self,
        trajectory_matrix: np.ndarray,
        uncertainty_set: Optional[UncertaintySet],
        time_offset: float,
        out_matrix: np.ndarray,
    ):
        """
        Modifies trajectory risk matrix by broadening spatial influence regions where uncertainty is high.
        """
        if uncertainty_set is None or trajectory_matrix.size == 0:
            np.copyto(out_matrix, trajectory_matrix)
            return

        # Blend base trajectory risk with Phase 9 uncertainty grid if available
        if uncertainty_set.grid is not None and uncertainty_set.grid.grid is not None:
            unc_grid_matrix = uncertainty_set.grid.grid
            horizon_factor = 1.0 + 0.15 * time_offset

            if unc_grid_matrix.shape == trajectory_matrix.shape:
                expanded_unc = np.clip(unc_grid_matrix * horizon_factor, 0.0, 1.0)
                combined = trajectory_matrix + 0.3 * expanded_unc * (trajectory_matrix > 0.05)
                np.clip(combined, 0.0, 1.0, out=out_matrix)
            else:
                r = min(unc_grid_matrix.shape[0], trajectory_matrix.shape[0])
                c = min(unc_grid_matrix.shape[1], trajectory_matrix.shape[1])
                sub_unc = np.clip(unc_grid_matrix[:r, :c] * horizon_factor, 0.0, 1.0)
                sub_traj = trajectory_matrix[:r, :c]

                np.copyto(out_matrix, trajectory_matrix)
                out_matrix[:r, :c] = np.clip(sub_traj + 0.3 * sub_unc * (sub_traj > 0.05), 0.0, 1.0)
        else:
            np.copyto(out_matrix, trajectory_matrix)
