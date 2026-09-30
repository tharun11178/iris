"""
IRIS Uncertainty Manager (Phase 9).
Central manager orchestrating perception, tracking, velocity, heading, behavior, prediction horizon,
geometric ellipse generation, and spatial uncertainty grid mapping.
"""

import math
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from tracking.track import Track, TrackState
from prediction.trajectory import PredictionSet, PredictedTrajectory
from uncertainty.uncertainty_model import (
    UncertaintyState,
    UncertaintyEllipse,
    UncertaintyRegion,
    UncertaintyGrid,
    UncertaintySet,
)
from uncertainty.position_uncertainty import compute_position_uncertainty
from uncertainty.velocity_uncertainty import compute_velocity_uncertainty
from uncertainty.heading_uncertainty import compute_heading_uncertainty
from uncertainty.behavior_uncertainty import compute_behavior_uncertainty
from uncertainty.prediction_uncertainty import (
    compute_tracking_uncertainty,
    compute_prediction_horizon_uncertainty,
)
from uncertainty.config import (
    WEIGHT_POSITION,
    WEIGHT_VELOCITY,
    WEIGHT_HEADING,
    WEIGHT_TRACKING,
    WEIGHT_BEHAVIOR,
    WEIGHT_PREDICTION,
    HORIZON_GROWTH_RATE,
    MAX_UNCERTAINTY,
    CAR_UNCERTAINTY_MARGIN,
    TRUCK_UNCERTAINTY_MARGIN,
    MOTORCYCLE_UNCERTAINTY_MARGIN,
    PEDESTRIAN_UNCERTAINTY_MARGIN,
    CATTLE_UNCERTAINTY_MARGIN,
    BICYCLE_UNCERTAINTY_MARGIN,
)


class UncertaintyManager:
    """
    Orchestrates execution of sub-component uncertainty models and maps uncertainty-aware regions and grid.
    """

    def __init__(
        self,
        config: Optional[Any] = None,
        weight_position: float = WEIGHT_POSITION,
        weight_velocity: float = WEIGHT_VELOCITY,
        weight_heading: float = WEIGHT_HEADING,
        weight_tracking: float = WEIGHT_TRACKING,
        weight_behavior: float = WEIGHT_BEHAVIOR,
        weight_prediction: float = WEIGHT_PREDICTION,
    ):
        if isinstance(config, (float, int)):
            weight_position = config
            config = None

        self.config = config
        self.w_pos = weight_position if not (config and hasattr(config, "WEIGHT_POSITION")) else config.WEIGHT_POSITION
        self.w_vel = weight_velocity if not (config and hasattr(config, "WEIGHT_VELOCITY")) else config.WEIGHT_VELOCITY
        self.w_head = weight_heading if not (config and hasattr(config, "WEIGHT_HEADING")) else config.WEIGHT_HEADING
        self.w_track = weight_tracking if not (config and hasattr(config, "WEIGHT_TRACKING")) else config.WEIGHT_TRACKING
        self.w_behav = weight_behavior if not (config and hasattr(config, "WEIGHT_BEHAVIOR")) else config.WEIGHT_BEHAVIOR
        self.w_pred = weight_prediction if not (config and hasattr(config, "WEIGHT_PREDICTION")) else config.WEIGHT_PREDICTION

        self.last_uncertainty_set: Optional[UncertaintySet] = None

    def get_object_margin(self, object_type: Any) -> float:
        """Returns object class margin for uncertainty calculations."""
        type_str = object_type.name if hasattr(object_type, "name") else str(object_type)
        if type_str == "CATTLE":
            return CATTLE_UNCERTAINTY_MARGIN
        elif type_str == "PEDESTRIAN":
            return PEDESTRIAN_UNCERTAINTY_MARGIN
        elif type_str == "MOTORCYCLE":
            return MOTORCYCLE_UNCERTAINTY_MARGIN
        elif type_str == "BICYCLE":
            return BICYCLE_UNCERTAINTY_MARGIN
        elif type_str in ("TRUCK", "BUS"):
            return TRUCK_UNCERTAINTY_MARGIN
        return CAR_UNCERTAINTY_MARGIN

    def compute(
        self,
        tracks: List[Track],
        prediction_set: Optional[PredictionSet] = None,
        timestamp: float = 0.0,
        grid_rows: int = 40,
        grid_cols: int = 140,
        grid_res: float = 0.5,
        converter: Optional[Any] = None,
    ) -> UncertaintySet:
        """
        Executes complete uncertainty modeling pipeline for all active tracks.
        
        :param tracks: Active persistent Track objects.
        :param prediction_set: Optional PredictionSet from Phase 8 Motion Predictor.
        :param timestamp: Current simulation timestamp.
        :param grid_rows: Occupancy grid rows count.
        :param grid_cols: Occupancy grid cols count.
        :param grid_res: Grid resolution in meters.
        :param converter: CoordinateConverter instance.
        :return: UncertaintySet containing states, regions, and spatial UncertaintyGrid.
        """
        object_states: Dict[str, UncertaintyState] = {}
        regions: List[UncertaintyRegion] = []
        unc_grid = UncertaintyGrid(num_rows=grid_rows, num_cols=grid_cols, grid_res=grid_res)

        active_tracks = [t for t in tracks if t.state != TrackState.DELETED]

        for track in active_tracks:
            margin = self.get_object_margin(track.object_type)

            # 1. Compute Sub-Component Uncertainties
            percep_unc, pos_unc, sigma_x, sigma_y = compute_position_uncertainty(track, margin=margin)
            vel_unc = compute_velocity_uncertainty(track)
            head_unc = compute_heading_uncertainty(track)
            track_unc = compute_tracking_uncertainty(track)
            behav_unc = compute_behavior_uncertainty(track, prediction_set=prediction_set)

            # Baseline prediction model uncertainty
            pred_unc = 0.2 if track.speed >= 0.3 else 0.1

            # 2. Compute Overall Weighted Aggregate Uncertainty
            overall = (
                self.w_pos * pos_unc +
                self.w_vel * vel_unc +
                self.w_head * head_unc +
                self.w_track * track_unc +
                self.w_behav * behav_unc +
                self.w_pred * pred_unc
            )
            overall_clamped = min(MAX_UNCERTAINTY, max(0.0, overall))

            state = UncertaintyState(
                track_id=track.track_id,
                object_type=track.object_type,
                position_uncertainty=pos_unc,
                velocity_uncertainty=vel_unc,
                heading_uncertainty=head_unc,
                tracking_uncertainty=track_unc,
                behavior_uncertainty=behav_unc,
                prediction_uncertainty=pred_unc,
                perception_uncertainty=percep_unc,
                overall_uncertainty=round(overall_clamped, 4),
                timestamp=timestamp,
                sigma_x=sigma_x,
                sigma_y=sigma_y,
            )
            object_states[track.track_id] = state

            # 3. Generate Geometric Uncertainty Ellipses over Time Horizon
            ellipses: List[UncertaintyEllipse] = []
            time_offsets: List[float] = []

            # Locate predicted trajectories for this track
            t_list = []
            if prediction_set is not None:
                t_list = [tr for tr in prediction_set.trajectories if tr.track_id == track.track_id]

            if t_list and t_list[0].predicted_positions:
                nominal_traj = t_list[0]
                for idx, (px, py) in enumerate(nominal_traj.predicted_positions):
                    t_stamp = nominal_traj.timestamps[idx]
                    dt = t_stamp - timestamp

                    # Prediction uncertainty grows over horizon t
                    horizon_unc = compute_prediction_horizon_uncertainty(overall_clamped, dt)

                    # Expand ellipse dimensions with horizon growth
                    ellipse_sx = sigma_x * (1.0 + horizon_unc)
                    ellipse_sy = sigma_y * (1.0 + horizon_unc)
                    yaw = nominal_traj.heading

                    ell = UncertaintyEllipse(
                        center_x=px,
                        center_y=py,
                        sigma_x=round(ellipse_sx, 4),
                        sigma_y=round(ellipse_sy, 4),
                        orientation_yaw=yaw,
                        time_offset=round(dt, 2),
                        confidence=round(1.0 - horizon_unc, 3),
                    )
                    ellipses.append(ell)
                    time_offsets.append(round(dt, 2))

                    # 4. Rasterize spatial uncertainty onto UncertaintyGrid
                    if converter is not None:
                        r, c = converter.world_to_grid(px, py)
                        if 0 <= r < grid_rows and 0 <= c < grid_cols:
                            current_val = unc_grid.grid[r, c]
                            unc_grid.grid[r, c] = min(MAX_UNCERTAINTY, max(current_val, horizon_unc))
            else:
                # Fallback: Ellipse series over time horizon (t=0.0s, 1.0s, 2.0s, 3.0s)
                for t_step in [0.0, 1.0, 2.0, 3.0]:
                    ell = self._build_ellipse(
                        center=track.current_position,
                        sigma_x=sigma_x,
                        sigma_y=sigma_y,
                        heading=track.heading,
                        t_horizon=t_step,
                    )
                    ellipses.append(ell)
                    time_offsets.append(t_step)

            region = UncertaintyRegion(
                track_id=track.track_id,
                timestamp=timestamp,
                ellipses=ellipses,
                time_offsets=time_offsets,
                state=state,
                object_type=track.object_type,
            )
            regions.append(region)

        unc_set = UncertaintySet(
            timestamp=timestamp,
            object_states=object_states,
            regions=regions,
            uncertainty_grid=unc_grid,
        )

        self.last_uncertainty_set = unc_set
        return unc_set

    def evaluate_uncertainty(
        self,
        tracks: List[Track],
        prediction_set: Optional[PredictionSet] = None,
        current_time: float = 0.0,
    ) -> UncertaintySet:
        """Alias method for evaluating uncertainty set."""
        return self.compute(tracks, prediction_set, timestamp=current_time)

    def _build_ellipse(
        self,
        center: Tuple[float, float],
        sigma_x: float,
        sigma_y: float,
        heading: float,
        t_horizon: float = 0.0,
    ) -> UncertaintyEllipse:
        """Helper method to construct a growing uncertainty ellipse."""
        horizon_factor = 1.0 + HORIZON_GROWTH_RATE * t_horizon
        return UncertaintyEllipse(
            center_x=center[0],
            center_y=center[1],
            sigma_x=round(sigma_x * horizon_factor, 4),
            sigma_y=round(sigma_y * horizon_factor, 4),
            orientation_yaw=heading,
            time_offset=round(t_horizon, 2),
            confidence=round(1.0 - min(1.0, HORIZON_GROWTH_RATE * t_horizon), 3),
        )

    def build_uncertainty_grid(
        self,
        uncertainty_set: UncertaintySet,
        converter: Any,
        num_cols: int = 140,
        num_rows: int = 40,
        grid_res: float = 0.5,
    ) -> UncertaintyGrid:
        """Rasterizes uncertainty set into a spatial grid."""
        grid = UncertaintyGrid(num_rows=num_rows, num_cols=num_cols, grid_res=grid_res)
        if uncertainty_set and uncertainty_set.regions:
            for region in uncertainty_set.regions:
                peak_unc = region.state.overall_uncertainty if region.state else 1.0
                for ell in region.ellipses:
                    grid.rasterize_ellipse(ell, converter, peak_uncertainty=peak_unc)
        return grid

    def get_summary(self) -> Dict[str, Any]:
        """Returns diagnostic dictionary summary of last uncertainty set."""
        if self.last_uncertainty_set is None:
            return {
                "active_regions": 0,
                "active_uncertainty_objects": 0,
                "avg_overall_uncertainty": 0.0,
                "avg_position_sigma": 0.0,
                "avg_velocity_variance": 0.0,
                "peak_spatial_uncertainty": 0.0,
                "average_spatial_uncertainty": 0.0,
            }

        grid = self.last_uncertainty_set.uncertainty_grid
        peak_unc = grid.get_max_uncertainty() if grid else 0.0
        avg_unc = grid.get_average_uncertainty() if grid else 0.0

        regions = self.last_uncertainty_set.regions
        avg_overall = sum(r.state.overall_uncertainty for r in regions) / len(regions) if regions and regions[0].state else 0.0
        avg_pos_sigma = sum(r.state.position_sigma for r in regions) / len(regions) if regions and regions[0].state else 0.0
        avg_vel_var = sum(r.state.velocity_variance for r in regions) / len(regions) if regions and regions[0].state else 0.0

        return {
            "active_regions": len(self.last_uncertainty_set.regions),
            "active_uncertainty_objects": len(self.last_uncertainty_set.object_states),
            "avg_overall_uncertainty": round(avg_overall, 3),
            "avg_position_sigma": round(avg_pos_sigma, 3),
            "avg_velocity_variance": round(avg_vel_var, 3),
            "peak_spatial_uncertainty": round(peak_unc, 3),
            "average_spatial_uncertainty": round(avg_unc, 4),
        }
