"""
IRIS Risk Engine Facade (Phase 4)
Central spatial risk aggregation engine combining Traffic, Surface, Boundary,
and Collision risk models into a normalized Total Risk Grid.
"""

import numpy as np
from typing import Optional, Dict
from world.world_model import WorldModel
from risk_engine.risk_grid import RiskGrid
from risk_engine.traffic_risk import TrafficRiskModel
from risk_engine.surface_risk import SurfaceRiskModel
from risk_engine.boundary_risk import BoundaryRiskModel
from risk_engine.collision_risk import CollisionRiskModel
from risk_engine.config import (
    TRAFFIC_RISK_WEIGHT,
    SURFACE_RISK_WEIGHT,
    BOUNDARY_RISK_WEIGHT,
    COLLISION_RISK_WEIGHT,
)


class RiskEngine:
    """
    Central spatial Risk Engine facade.
    Reads current WorldModel and generates continuous RiskGrid matrices.
    """

    def __init__(
        self,
        w_traffic: float = TRAFFIC_RISK_WEIGHT,
        w_surface: float = SURFACE_RISK_WEIGHT,
        w_boundary: float = BOUNDARY_RISK_WEIGHT,
        w_collision: float = COLLISION_RISK_WEIGHT,
    ):
        self.w_traffic = w_traffic
        self.w_surface = w_surface
        self.w_boundary = w_boundary
        self.w_collision = w_collision

        self.traffic_model = TrafficRiskModel()
        self.surface_model = SurfaceRiskModel()
        self.boundary_model = BoundaryRiskModel()
        self.collision_model = CollisionRiskModel()

        self.risk_grid: Optional[RiskGrid] = None

    def update(self, world_model: WorldModel) -> RiskGrid:
        """
        Recalculates all component risk matrices from the current WorldModel.
        """
        num_rows = world_model.grid.num_rows
        num_cols = world_model.grid.num_cols

        if self.risk_grid is None or self.risk_grid.num_rows != num_rows or self.risk_grid.num_cols != num_cols:
            self.risk_grid = RiskGrid(num_rows, num_cols, world_model.grid.grid_res)
        else:
            self.risk_grid.clear()

        # 1. Compute Individual Risk Components
        self.traffic_model.compute(world_model, self.risk_grid.traffic_risk)
        self.surface_model.compute(world_model, self.risk_grid.surface_risk)
        self.boundary_model.compute(world_model, self.risk_grid.boundary_risk)
        self.collision_model.compute(world_model, self.risk_grid.collision_risk)

        # 2. Weighted Sum Combination
        total = (
            self.w_traffic * self.risk_grid.traffic_risk +
            self.w_surface * self.risk_grid.surface_risk +
            self.w_boundary * self.risk_grid.boundary_risk +
            self.w_collision * self.risk_grid.collision_risk
        )

        # 3. Preserve Critical Constraints (Occupied / Outside-road cells receive max risk)
        total = np.maximum(total, self.risk_grid.collision_risk * 0.95)

        self.risk_grid.total_risk[:] = total
        self.risk_grid.normalize()

        return self.risk_grid

    def get_risk(self, row: int, col: int) -> float:
        """
        Returns normalized total risk at grid coordinate (row, col).
        """
        if self.risk_grid is not None:
            return self.risk_grid.get_risk(row, col)
        return 0.0

    def get_component_risk(self, row: int, col: int) -> Dict[str, float]:
        """
        Returns risk breakdown dictionary at grid coordinate (row, col).
        """
        if self.risk_grid is not None:
            return self.risk_grid.get_component_risk(row, col)
        return {"traffic": 0.0, "surface": 0.0, "boundary": 0.0, "collision": 0.0, "total": 0.0}
