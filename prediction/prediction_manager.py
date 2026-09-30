"""
IRIS Prediction Manager (Phase 8).
Central manager orchestrating motion prediction across active persistent tracks,
generating nominal trajectories, multi-hypothesis branches, envelopes, and future grid occupancy.
"""

import math
from typing import List, Optional, Dict, Any, Tuple
from tracking.track import Track, TrackState
from prediction.trajectory import (
    PredictedTrajectory,
    PredictionHypothesis,
    PredictionSet,
    FutureOccupiedCell,
    FutureOccupancy,
)
from prediction.behavior_model import get_behavior_profile, classify_motion_pattern, BehaviorCategory
from prediction.motion_predictor import MotionPredictor
from prediction.config import (
    PREDICTION_HORIZON,
    PREDICTION_TIME_STEP,
    DEFAULT_MODEL,
    CONFIDENCE_DECAY_RATE,
)


class PredictionManager:
    """
    Manages execution of trajectory prediction algorithms and future occupancy mapping.
    """

    def __init__(
        self,
        predictor: Optional[MotionPredictor] = None,
        default_model: str = DEFAULT_MODEL,
        horizon: float = PREDICTION_HORIZON,
        time_step: float = PREDICTION_TIME_STEP,
    ):
        self.predictor = predictor if predictor is not None else MotionPredictor(
            horizon=horizon,
            time_step=time_step,
            decay_rate=CONFIDENCE_DECAY_RATE,
        )
        self.default_model = default_model
        self.last_prediction_set: Optional[PredictionSet] = None
        self.last_future_occupancies: List[FutureOccupancy] = []

    def predict(
        self,
        tracks: List[Track],
        timestamp: float = 0.0,
        road_evaluator: Optional[Any] = None,
    ) -> PredictionSet:
        """
        Executes frame-level trajectory prediction pipeline for all active non-deleted tracks.
        
        :param tracks: List of active persistent Track objects from Phase 7 TrackManager.
        :param timestamp: Current simulation timestamp in seconds.
        :param road_evaluator: Optional road boundary/drivability evaluator function.
        :return: PredictionSet instance.
        """
        trajectories: List[PredictedTrajectory] = []
        hypotheses: List[PredictionHypothesis] = []

        active_tracks = [t for t in tracks if t.state != TrackState.DELETED]

        for track in active_tracks:
            profile = get_behavior_profile(track.object_type)
            motion_cat = classify_motion_pattern(track)

            # 1. Generate Nominal Trajectory (Constant Velocity or Acceleration)
            if profile.preferred_model == "constant_acceleration" and track.acceleration:
                nominal_traj = self.predictor.predict_constant_acceleration(
                    track=track,
                    start_timestamp=timestamp,
                    road_evaluator=road_evaluator,
                )
            else:
                nominal_traj = self.predictor.predict_constant_velocity(
                    track=track,
                    start_timestamp=timestamp,
                    road_evaluator=road_evaluator,
                )
            trajectories.append(nominal_traj)

            # 2. Generate Multi-Hypothesis Prediction for Irregular Objects (Cattle, Pedestrians)
            if profile.supports_multi_hypothesis or motion_cat == BehaviorCategory.IRREGULAR:
                hypos = self.predictor.predict_multi_hypothesis(
                    track=track,
                    start_timestamp=timestamp,
                    road_evaluator=road_evaluator,
                )
                hypotheses.extend(hypos)

        prediction_set = PredictionSet(
            timestamp=timestamp,
            prediction_horizon=self.predictor.horizon,
            trajectories=trajectories,
            hypotheses=hypotheses,
            prediction_count=len(trajectories),
        )

        self.last_prediction_set = prediction_set
        return prediction_set

    def convert_to_future_occupancy(
        self,
        prediction_set: Optional[PredictionSet],
        converter: Any,
        grid_cols: int,
        grid_rows: int,
        grid_res: float,
    ) -> List[FutureOccupancy]:
        """
        Converts predicted trajectories into discrete future occupancy grid cell time-series.
        
        :param prediction_set: PredictionSet containing trajectories & hypotheses.
        :param converter: World CoordinateConverter instance.
        :param grid_cols: Number of grid columns.
        :param grid_rows: Number of grid rows.
        :param grid_res: Grid resolution in meters.
        :return: List of FutureOccupancy objects.
        """
        if prediction_set is None or not prediction_set.trajectories:
            self.last_future_occupancies = []
            return []

        future_occupancies: List[FutureOccupancy] = []

        for traj in prediction_set.trajectories:
            cell_list: List[FutureOccupiedCell] = []
            world_positions: List[Tuple[float, float]] = []

            for idx, (px, py) in enumerate(traj.predicted_positions):
                t_stamp = traj.timestamps[idx]
                dt = t_stamp - prediction_set.timestamp
                world_positions.append((px, py))

                r, c = converter.world_to_grid(px, py)
                if 0 <= r < grid_rows and 0 <= c < grid_cols:
                    # Calculate decayed confidence at step dt
                    step_conf = max(0.1, traj.confidence * (1.0 - CONFIDENCE_DECAY_RATE * dt))
                    f_cell = FutureOccupiedCell(
                        grid_r=r,
                        grid_c=c,
                        x_world=px,
                        y_world=py,
                        timestamp=t_stamp,
                        time_offset=round(dt, 2),
                        confidence=round(step_conf, 3),
                    )
                    cell_list.append(f_cell)

            f_occ = FutureOccupancy(
                track_id=traj.track_id,
                timestamp=prediction_set.timestamp,
                grid_cells=cell_list,
                world_positions=world_positions,
                occupancy_confidence=traj.confidence,
                hypothesis_id="NOMINAL",
            )
            future_occupancies.append(f_occ)

        # Process multi-hypotheses as well
        for hypo in prediction_set.hypotheses:
            traj = hypo.trajectory
            cell_list = []
            world_positions = []

            for idx, (px, py) in enumerate(traj.predicted_positions):
                t_stamp = traj.timestamps[idx]
                dt = t_stamp - prediction_set.timestamp
                world_positions.append((px, py))

                r, c = converter.world_to_grid(px, py)
                if 0 <= r < grid_rows and 0 <= c < grid_cols:
                    step_conf = max(0.1, hypo.confidence * (1.0 - CONFIDENCE_DECAY_RATE * dt))
                    f_cell = FutureOccupiedCell(
                        grid_r=r,
                        grid_c=c,
                        x_world=px,
                        y_world=py,
                        timestamp=t_stamp,
                        time_offset=round(dt, 2),
                        confidence=round(step_conf, 3),
                    )
                    cell_list.append(f_cell)

            f_occ = FutureOccupancy(
                track_id=hypo.track_id,
                timestamp=prediction_set.timestamp,
                grid_cells=cell_list,
                world_positions=world_positions,
                occupancy_confidence=hypo.confidence,
                hypothesis_id=hypo.hypothesis_id,
            )
            future_occupancies.append(f_occ)

        self.last_future_occupancies = future_occupancies
        return future_occupancies

    def get_summary(self) -> Dict[str, Any]:
        """Returns diagnostic dictionary summary of last prediction set."""
        if self.last_prediction_set is None:
            return {
                "total_trajectories": 0,
                "total_hypotheses": 0,
                "future_occupancies_count": 0,
            }
        return {
            "total_trajectories": len(self.last_prediction_set.trajectories),
            "total_hypotheses": len(self.last_prediction_set.hypotheses),
            "future_occupancies_count": len(self.last_future_occupancies),
        }
