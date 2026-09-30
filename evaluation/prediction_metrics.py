"""
IRIS Motion Prediction Evaluation Metrics (Phase 8).
Computes quantitative prediction metrics including Average Displacement Error (ADE),
Final Displacement Error (FDE), and Multi-Hypothesis Coverage.
"""

import math
from typing import List, Dict, Any, Tuple, Optional
from prediction.trajectory import PredictedTrajectory, PredictionHypothesis, PredictionSet


class PredictionEvaluator:
    """
    Evaluates trajectory predictions against actual simulation ground-truth future positions over time.
    """

    def __init__(self, default_horizon: float = 3.0):
        self.default_horizon = default_horizon

    def evaluate_trajectory(
        self,
        predicted_trajectory: PredictedTrajectory,
        ground_truth_future_positions: List[Tuple[float, float]],
    ) -> Dict[str, float]:
        """
        Computes ADE and FDE for a single predicted trajectory against actual ground-truth future positions.
        
        :param predicted_trajectory: PredictedTrajectory object.
        :param ground_truth_future_positions: List of actual future (x, y) coordinates.
        :return: Dictionary containing 'ade' and 'fde' in meters.
        """
        pred_pos = predicted_trajectory.predicted_positions
        if not pred_pos or not ground_truth_future_positions:
            return {"ade": 0.0, "fde": 0.0}

        n_steps = min(len(pred_pos), len(ground_truth_future_positions))
        if n_steps == 0:
            return {"ade": 0.0, "fde": 0.0}

        errors = []
        for i in range(n_steps):
            px, py = pred_pos[i]
            gt_x, gt_y = ground_truth_future_positions[i]
            err = math.hypot(px - gt_x, py - gt_y)
            errors.append(err)

        ade = float(sum(errors) / len(errors))
        fde = float(errors[-1])

        return {
            "ade": round(ade, 4),
            "fde": round(fde, 4),
        }

    def evaluate_hypothesis_coverage(
        self,
        hypotheses: List[PredictionHypothesis],
        ground_truth_future_positions: List[Tuple[float, float]],
        margin_threshold: float = 1.2,
    ) -> Tuple[bool, Optional[str], float]:
        """
        Evaluates whether actual ground-truth future path falls within at least one hypothesis envelope.
        
        :param hypotheses: List of PredictionHypothesis objects for a single track.
        :param ground_truth_future_positions: List of actual future (x, y) coordinates.
        :param margin_threshold: Allowable spatial margin in meters.
        :return: Tuple of (covered: bool, best_hypothesis_id: str, min_fde: float).
        """
        if not hypotheses or not ground_truth_future_positions:
            return False, None, 0.0

        best_h_id = None
        min_fde = float("inf")
        covered = False

        for hypo in hypotheses:
            res = self.evaluate_trajectory(hypo.trajectory, ground_truth_future_positions)
            fde = res["fde"]
            if fde < min_fde:
                min_fde = fde
                best_h_id = hypo.hypothesis_id

            if fde <= margin_threshold or res["ade"] <= margin_threshold:
                covered = True

        return covered, best_h_id, round(min_fde, 4)
