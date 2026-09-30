"""
IRIS Perception Evaluation Metrics (Phase 6).
Provides spatial matching and quantitative perception evaluation metrics
(Precision, Recall, F1 Score, Mean Position Error) overall and per object class.
"""

import math
from typing import List, Dict, Any, Tuple
from perception.detected_object import DetectedObject
from perception.object_classes import ObjectClass
from perception.config import MATCH_DISTANCE_THRESHOLD


class PerceptionEvaluator:
    """
    Evaluates perception detection output against simulation ground truth.
    """

    def __init__(self, match_threshold: float = MATCH_DISTANCE_THRESHOLD):
        self.match_threshold = match_threshold

    def evaluate(
        self,
        ground_truth_actors: List[Any],
        detections: List[DetectedObject],
        ego_pos_world: Tuple[float, float] = (0.0, 0.0),
        detection_range: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Computes perception evaluation metrics comparing ground truth within range against perceived detections.
        
        :param ground_truth_actors: List of simulation TrafficActor instances or dicts.
        :param detections: List of perceived DetectedObject instances.
        :param ego_pos_world: Ego vehicle position (wx, wy) in meters.
        :param detection_range: Maximum detection range in meters.
        :return: Metric breakdown dictionary containing overall and per-class metrics.
        """
        # 1. Filter ground truth actors within range
        gt_in_range = []
        for actor in ground_truth_actors:
            if hasattr(actor, "x") and hasattr(actor, "y"):
                # Sim coordinates to World coordinates (y_world = y_sim + 9.0 by default)
                wx, wy = actor.x, actor.y + 9.0
                a_type = ObjectClass.from_actor_type(actor.actor_type)
                a_id = getattr(actor, "actor_id", len(gt_in_range))
            elif isinstance(actor, dict):
                wx, wy = actor.get("x", 0.0), actor.get("y", 0.0)
                a_type = ObjectClass.from_actor_type(actor.get("type", "CAR"))
                a_id = actor.get("id", len(gt_in_range))
            else:
                continue

            dist = math.hypot(wx - ego_pos_world[0], wy - ego_pos_world[1])
            if dist <= detection_range:
                gt_in_range.append({
                    "id": a_id,
                    "type": a_type,
                    "x": wx,
                    "y": wy,
                })

        # 2. Greedy spatial matching by distance and class match
        matched_gt_indices = set()
        matched_det_indices = set()
        tp_position_errors = []

        # Sort detections by confidence descending for greedy assignment
        sorted_det_indices = sorted(range(len(detections)), key=lambda i: detections[i].confidence, reverse=True)

        for det_idx in sorted_det_indices:
            det = detections[det_idx]
            best_gt_idx = None
            best_dist = float("inf")

            for gt_idx, gt in enumerate(gt_in_range):
                if gt_idx in matched_gt_indices:
                    continue

                # Class match check
                if det.object_type == gt["type"]:
                    dist = math.hypot(det.position[0] - gt["x"], det.position[1] - gt["y"])
                    if dist <= self.match_threshold and dist < best_dist:
                        best_dist = dist
                        best_gt_idx = gt_idx

            if best_gt_idx is not None:
                matched_gt_indices.add(best_gt_idx)
                matched_det_indices.add(det_idx)
                tp_position_errors.append(best_dist)

        tp = len(matched_det_indices)
        fp = len(detections) - tp
        fn = len(gt_in_range) - tp

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if len(gt_in_range) == 0 else 0.0)
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        mean_pos_error = float(sum(tp_position_errors) / len(tp_position_errors)) if tp_position_errors else 0.0

        # 3. Compute Per-Class Metrics
        per_class_metrics = {}
        for cls in ObjectClass:
            cls_gt = [gt for gt in gt_in_range if gt["type"] == cls]
            cls_det = [det for det in detections if det.object_type == cls]

            cls_tp = 0
            cls_pos_errors = []
            cls_matched_gt = set()

            for det in cls_det:
                best_gt_i = None
                best_d = float("inf")
                for i, gt in enumerate(cls_gt):
                    if i in cls_matched_gt:
                        continue
                    d = math.hypot(det.position[0] - gt["x"], det.position[1] - gt["y"])
                    if d <= self.match_threshold and d < best_d:
                        best_d = d
                        best_gt_i = i

                if best_gt_i is not None:
                    cls_matched_gt.add(best_gt_i)
                    cls_tp += 1
                    cls_pos_errors.append(best_d)

            cls_fp = len(cls_det) - cls_tp
            cls_fn = len(cls_gt) - cls_tp
            cls_prec = cls_tp / (cls_tp + cls_fp) if (cls_tp + cls_fp) > 0 else 1.0
            cls_rec = cls_tp / (cls_tp + cls_fn) if (cls_tp + cls_fn) > 0 else (1.0 if len(cls_gt) == 0 else 0.0)
            cls_f1 = (2.0 * cls_prec * cls_rec / (cls_prec + cls_rec)) if (cls_prec + cls_rec) > 0 else 0.0

            per_class_metrics[cls.name] = {
                "ground_truth_count": len(cls_gt),
                "detection_count": len(cls_det),
                "true_positives": cls_tp,
                "false_positives": cls_fp,
                "false_negatives": cls_fn,
                "precision": round(cls_prec, 4),
                "recall": round(cls_rec, 4),
                "f1_score": round(cls_f1, 4),
                "mean_position_error": round(float(sum(cls_pos_errors) / len(cls_pos_errors)), 4) if cls_pos_errors else 0.0,
            }

        return {
            "ground_truth_count": len(gt_in_range),
            "detection_count": len(detections),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "mean_position_error": round(mean_pos_error, 4),
            "per_class": per_class_metrics,
        }
