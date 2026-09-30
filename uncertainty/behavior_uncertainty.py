"""
IRIS Behavior Uncertainty Calculator (Phase 9).
Estimates behavior uncertainty and multi-hypothesis spatial disagreement between predicted trajectory branches.
"""

import math
from typing import List, Optional
from tracking.track import Track
from prediction.trajectory import PredictionHypothesis, PredictionSet
from uncertainty.config import MAX_UNCERTAINTY


def compute_behavior_uncertainty(
    track: Track,
    prediction_set: Optional[PredictionSet] = None,
) -> float:
    """
    Computes behavior uncertainty score [0.0, 1.0] based on track object class,
    motion profile, and spatial disagreement between multi-hypothesis trajectory branches.
    
    :param track: Active Track instance.
    :param prediction_set: Optional PredictionSet from Phase 8.
    :return: Normalized behavior uncertainty score.
    """
    type_str = track.object_type.name if hasattr(track.object_type, "name") else str(track.object_type)

    if prediction_set is None or not prediction_set.hypotheses:
        # Default category baseline behavior uncertainty
        if type_str == "CATTLE":
            return 0.7
        elif type_str == "PEDESTRIAN":
            return 0.5
        elif type_str == "MOTORCYCLE":
            return 0.4
        return 0.2

    # Collect hypotheses for this track
    track_hypos = [h for h in prediction_set.hypotheses if h.track_id == track.track_id]
    if len(track_hypos) <= 1:
        # Single hypothesis -> low behavior uncertainty
        return 0.2 if type_str not in ("CATTLE", "PEDESTRIAN") else 0.4

    # Calculate spatial disagreement (max distance between final predicted positions of hypotheses)
    final_positions = []
    for h in track_hypos:
        if h.trajectory and h.trajectory.predicted_positions:
            final_positions.append(h.trajectory.predicted_positions[-1])

    if len(final_positions) < 2:
        return 0.4

    max_disagreement = 0.0
    for i in range(len(final_positions)):
        for j in range(i + 1, len(final_positions)):
            dist = math.hypot(
                final_positions[i][0] - final_positions[j][0],
                final_positions[i][1] - final_positions[j][1],
            )
            if dist > max_disagreement:
                max_disagreement = dist

    # Normalize max_disagreement (e.g. 5.0m max distance -> 1.0 score)
    disagreement_score = min(MAX_UNCERTAINTY, max_disagreement / 5.0)

    return round(disagreement_score, 4)


class BehaviorUncertaintyEstimator:
    def __init__(self, config=None):
        self.config = config

    def estimate(
        self,
        trajectories: Optional[List] = None,
        hypotheses: Optional[List] = None,
        track: Optional[Track] = None,
        prediction_set: Optional[PredictionSet] = None,
    ) -> float:
        if hypotheses is None and isinstance(trajectories, list) and len(trajectories) > 0 and hasattr(trajectories[0], "trajectory"):
            hypotheses = trajectories

        if hypotheses is not None and len(hypotheses) > 0:
            final_positions = []
            for h in hypotheses:
                traj = getattr(h, "trajectory", None)
                if traj and hasattr(traj, "predicted_positions") and traj.predicted_positions:
                    final_positions.append(traj.predicted_positions[-1])
            if len(final_positions) < 2:
                return 0.0
            max_dis = 0.0
            for i in range(len(final_positions)):
                for j in range(i + 1, len(final_positions)):
                    dist = math.hypot(final_positions[i][0] - final_positions[j][0], final_positions[i][1] - final_positions[j][1])
                    if dist > max_dis:
                        max_dis = dist
            return round(min(1.0, max_dis / 5.0), 4)

        if track is not None:
            return compute_behavior_uncertainty(track, prediction_set)
        return 0.0

