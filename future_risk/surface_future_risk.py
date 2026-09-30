"""
IRIS Surface Future Risk Calculator (Phase 10).
Persists static Phase 5 road surface hazard risk (potholes, waterlogging, speed breakers, debris)
across all future timesteps t in [0.0s, 3.0s].
"""

import numpy as np
from typing import Optional
from world.world_model import WorldModel
from risk_engine.surface_risk import SurfaceRiskModel


class SurfaceFutureRiskModel:
    """
    Computes static surface hazard risk persisting across the future time horizon.
    """

    def __init__(self):
        self.surface_risk_model = SurfaceRiskModel()
        self.cached_surface_risk: Optional[np.ndarray] = None

    def clear_cache(self):
        """Clears cached surface risk matrix."""
        self.cached_surface_risk = None

    def compute_surface_future_risk(self, world_model: WorldModel, out_matrix: np.ndarray, time_offset: float = 0.0):
        """
        Populates out_matrix with persistent road surface hazard risk for time_offset t.
        Static hazards (potholes, waterlogging, debris) remain spatially fixed across all future timesteps.
        """
        num_rows = world_model.grid.num_rows
        num_cols = world_model.grid.num_cols

        if self.cached_surface_risk is None or self.cached_surface_risk.shape != (num_rows, num_cols):
            self.cached_surface_risk = np.zeros((num_rows, num_cols), dtype=np.float64)
            self.surface_risk_model.compute(world_model, self.cached_surface_risk)

        np.copyto(out_matrix, self.cached_surface_risk)
