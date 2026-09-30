"""
IRIS Future Risk Engine Facade (Phase 10).
Orchestrates current spatial baseline risk, dynamic trajectory risk projection, Phase 9 uncertainty expansion,
static surface hazard persistence, and road boundary constraints into a spatiotemporal FutureRiskField.
"""

import numpy as np
from typing import Optional, List, Dict, Any

from world.world_model import WorldModel
from world.cell import CellState
from risk_engine.risk_engine import RiskEngine
from risk_engine.risk_grid import RiskGrid
from risk_engine.boundary_risk import BoundaryRiskModel
from risk_engine.collision_risk import CollisionRiskModel

from future_risk.config import (
    FUTURE_RISK_HORIZON,
    FUTURE_RISK_TIME_STEP,
    TRAFFIC_RISK_WEIGHT,
    SURFACE_RISK_WEIGHT,
    BOUNDARY_RISK_WEIGHT,
    COLLISION_RISK_WEIGHT,
    HYPOTHESIS_AGGREGATION_METHOD,
)
from future_risk.future_risk_field import FutureRiskField
from future_risk.trajectory_risk import TrajectoryRiskModel
from future_risk.uncertainty_risk import UncertaintyRiskModel
from future_risk.surface_future_risk import SurfaceFutureRiskModel
from future_risk.temporal_risk import TemporalRiskModel


class FutureRiskEngine:
    """
    Central facade for generating the spatiotemporal FutureRiskField over time horizon t in [0.0s, 3.0s].
    """

    def __init__(
        self,
        horizon: float = FUTURE_RISK_HORIZON,
        time_step: float = FUTURE_RISK_TIME_STEP,
        w_traffic: float = TRAFFIC_RISK_WEIGHT,
        w_surface: float = SURFACE_RISK_WEIGHT,
        w_boundary: float = BOUNDARY_RISK_WEIGHT,
        w_collision: float = COLLISION_RISK_WEIGHT,
        aggregation_method: str = HYPOTHESIS_AGGREGATION_METHOD,
    ):
        self.horizon = horizon
        self.time_step = time_step
        self.w_traffic = w_traffic
        self.w_surface = w_surface
        self.w_boundary = w_boundary
        self.w_collision = w_collision

        self.current_risk_engine = RiskEngine(
            w_traffic=w_traffic,
            w_surface=w_surface,
            w_boundary=w_boundary,
            w_collision=w_collision,
        )
        self.trajectory_model = TrajectoryRiskModel(aggregation_method=aggregation_method)
        self.uncertainty_model = UncertaintyRiskModel()
        self.surface_future_model = SurfaceFutureRiskModel()
        self.boundary_model = BoundaryRiskModel()
        self.collision_model = CollisionRiskModel()
        self.temporal_model = TemporalRiskModel(horizon=horizon, time_step=time_step)

        self.last_risk_field: Optional[FutureRiskField] = None

    def compute_future_risk_field(self, world_model: WorldModel) -> FutureRiskField:
        """
        Executes complete Future Risk Engine pipeline across all discrete time steps t.
        
        :param world_model: WorldModel instance containing grid, surface_model, dynamic_actors, tracks, prediction_set, uncertainty_set.
        :return: FutureRiskField object containing 16 time-discretized RiskGrid instances.
        """
        num_rows = world_model.grid.num_rows
        num_cols = world_model.grid.num_cols
        sim_time = getattr(world_model, "sim_time", 0.0)

        # 1. Update Current Baseline Risk (Phase 4) for t=0.0s
        current_risk_grid = self.current_risk_engine.update(world_model)

        # 2. Generate Discrete Timestamps
        timestamps = self.temporal_model.generate_timestamps(start_time=0.0)
        risk_grids: List[RiskGrid] = []

        # Extract tracks, predictions, and uncertainty set
        tracks = [a["track"] for a in world_model.dynamic_actors if "track" in a]
        prediction_set = getattr(world_model, "prediction_set", None)
        uncertainty_set = getattr(world_model, "uncertainty_set", None)
        active_track_ids = [t.track_id for t in tracks]

        # 3. Precompute Static Surface & Boundary Risk Matrices (persist across all future timesteps)
        surface_matrix = np.zeros((num_rows, num_cols), dtype=np.float64)
        boundary_matrix = np.zeros((num_rows, num_cols), dtype=np.float64)

        self.surface_future_model.compute_surface_future_risk(world_model, surface_matrix, time_offset=0.0)
        self.boundary_model.compute(world_model, boundary_matrix)

        # 4. Generate RiskGrid for Each Discrete Timestep t
        for idx, t_offset in enumerate(timestamps):
            step_grid = RiskGrid(num_rows, num_cols, world_model.grid.grid_res)
            np.copyto(step_grid.surface_risk, surface_matrix)
            np.copyto(step_grid.boundary_risk, boundary_matrix)

            if idx == 0:
                # t = 0.0s: Exact match to Current Baseline Risk (Phase 4)
                np.copyto(step_grid.traffic_risk, current_risk_grid.traffic_risk)
                np.copyto(step_grid.collision_risk, current_risk_grid.collision_risk)
                np.copyto(step_grid.total_risk, current_risk_grid.total_risk)
            else:
                # t > 0.0s: Calculate dynamic predicted trajectory risk
                raw_traj_matrix = np.zeros((num_rows, num_cols), dtype=np.float64)
                self.trajectory_model.compute_timestep_trajectory_risk(
                    tracks=tracks,
                    prediction_set=prediction_set,
                    time_offset=t_offset,
                    world_model=world_model,
                    out_matrix=raw_traj_matrix,
                )

                # Apply Phase 9 uncertainty spatial expansion
                exp_traj_matrix = np.zeros((num_rows, num_cols), dtype=np.float64)
                self.uncertainty_model.apply_uncertainty_expansion(
                    trajectory_matrix=raw_traj_matrix,
                    uncertainty_set=uncertainty_set,
                    time_offset=t_offset,
                    out_matrix=exp_traj_matrix,
                )

                np.copyto(step_grid.traffic_risk, exp_traj_matrix)
                # Collision risk for future frames is driven by predicted traffic footprint
                np.copyto(step_grid.collision_risk, exp_traj_matrix * 0.95)

                # Combine component risk weighted sum
                total = (
                    self.w_traffic * step_grid.traffic_risk +
                    self.w_surface * step_grid.surface_risk +
                    self.w_boundary * step_grid.boundary_risk +
                    self.w_collision * step_grid.collision_risk
                )

                # Preserve Occupied / Boundary collision bounds
                total = np.maximum(total, step_grid.collision_risk * 0.95)
                np.copyto(step_grid.total_risk, total)
                step_grid.normalize()

            # 5. Enforce Non-Traversable Safety Constraints
            # Non-traversable cells (OUTSIDE_ROAD, ROAD_BOUNDARY) MUST remain max risk
            for r in range(num_rows):
                for c in range(num_cols):
                    cell = world_model.grid.cells[r][c]
                    if cell.state in (CellState.OUTSIDE_ROAD, CellState.ROAD_BOUNDARY):
                        step_grid.total_risk[r, c] = 1.0
                        step_grid.boundary_risk[r, c] = 1.0

            risk_grids.append(step_grid)

        field = FutureRiskField(
            timestamp=sim_time,
            prediction_horizon=self.horizon,
            time_step=self.time_step,
            risk_grids=risk_grids,
            timestamps=timestamps,
            active_tracks=active_track_ids,
        )

        self.last_risk_field = field
        return field

    def update(
        self,
        world_model: WorldModel,
        prediction_set: Optional[Any] = None,
        uncertainty_set: Optional[Any] = None,
        sim_time: float = 0.0,
    ) -> FutureRiskField:
        """
        Standardized update method for FutureRiskEngine facade.
        """
        if prediction_set is not None:
            setattr(world_model, "prediction_set", prediction_set)
        if uncertainty_set is not None:
            setattr(world_model, "uncertainty_set", uncertainty_set)
        if sim_time > 0.0:
            world_model.sim_time = sim_time
        return self.compute_future_risk_field(world_model)

    def get_summary(self) -> Dict[str, Any]:
        """Returns diagnostic summary of last computed FutureRiskField."""
        if self.last_risk_field is None:
            return {
                "horizon": self.horizon,
                "time_step": self.time_step,
                "num_timesteps": 0,
                "maximum_risk": 0.0,
                "average_risk": 0.0,
            }

        return self.last_risk_field.to_dict()
