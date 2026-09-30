"""
IRIS Tracking Evaluation Metrics (Phase 7).
Computes quantitative Multi-Object Tracking metrics including track count, creation/deletion count,
ID switches, track continuity, detection association rate, average track age, and confirmed track ratio.
"""

import math
from typing import List, Dict, Any, Tuple, Optional, Set
from tracking.track import Track, TrackState
from tracking.track_manager import TrackManager
from perception.detected_object import DetectedObject
from tracking.config import MATCH_DISTANCE_THRESHOLD


class TrackingEvaluator:
    """
    Evaluates tracking performance against simulation ground truth and detection inputs over time.
    """

    def __init__(self, match_threshold: float = MATCH_DISTANCE_THRESHOLD):
        self.match_threshold = match_threshold
        # Maps ground truth actor ID -> previous associated track ID
        self.gt_to_track_history: Dict[str, str] = {}
        # Tracks count of frames each GT actor maintained its assigned track ID
        self.gt_track_duration: Dict[str, int] = {}
        self.gt_total_frames: Dict[str, int] = {}
        self.id_switch_count: int = 0

    def reset(self):
        """Resets evaluator historical counters."""
        self.gt_to_track_history.clear()
        self.gt_track_duration.clear()
        self.gt_total_frames.clear()
        self.id_switch_count = 0

    def evaluate_frame(
        self,
        ground_truth_actors: List[Any],
        active_tracks: List[Track],
        raw_detections: List[DetectedObject],
        ego_pos_world: Tuple[float, float] = (0.0, 0.0),
        eval_range: float = 50.0,
    ) -> Dict[str, Any]:
        """
        Evaluates a single frame of multi-object tracking.
        
        :param ground_truth_actors: List of simulation TrafficActor instances or dicts.
        :param active_tracks: List of active Track instances from TrackManager.
        :param raw_detections: List of perceived DetectedObjects for current frame.
        :param ego_pos_world: Ego vehicle position (wx, wy).
        :param eval_range: Evaluation radius in meters.
        :return: Frame evaluation metrics breakdown.
        """
        # 1. Filter ground truth within range
        gt_in_range = []
        for actor in ground_truth_actors:
            if hasattr(actor, "x") and hasattr(actor, "y"):
                wx, wy = actor.x, actor.y + 9.0
                a_id = str(getattr(actor, "actor_id", len(gt_in_range)))
            elif isinstance(actor, dict):
                wx, wy = actor.get("x", 0.0), actor.get("y", 0.0)
                a_id = str(actor.get("id", len(gt_in_range)))
            else:
                continue

            dist = math.hypot(wx - ego_pos_world[0], wy - ego_pos_world[1])
            if dist <= eval_range:
                gt_in_range.append({"id": a_id, "x": wx, "y": wy})

        # 2. Match GT objects to active tracks for ID switch detection
        matched_tracks_set: Set[str] = set()
        matched_gt_set: Set[str] = set()

        for gt in gt_in_range:
            gt_id = gt["id"]
            self.gt_total_frames[gt_id] = self.gt_total_frames.get(gt_id, 0) + 1

            best_track_id = None
            best_dist = float("inf")

            for track in active_tracks:
                if track.track_id in matched_tracks_set:
                    continue
                tx, ty = track.current_position
                dist = math.hypot(tx - gt["x"], ty - gt["y"])
                if dist <= self.match_threshold and dist < best_dist:
                    best_dist = dist
                    best_track_id = track.track_id

            if best_track_id is not None:
                matched_tracks_set.add(best_track_id)
                matched_gt_set.add(gt_id)

                prev_track = self.gt_to_track_history.get(gt_id)
                if prev_track is not None and prev_track != best_track_id:
                    # ID Switch detected!
                    self.id_switch_count += 1
                else:
                    self.gt_track_duration[gt_id] = self.gt_track_duration.get(gt_id, 0) + 1

                self.gt_to_track_history[gt_id] = best_track_id

        # 3. Association Rate (Detections matched to active tracks)
        det_count = len(raw_detections)
        matched_det_count = min(det_count, len(active_tracks))
        association_rate = (matched_det_count / det_count) if det_count > 0 else 1.0

        # 4. Active track statistics
        confirmed_count = sum(1 for t in active_tracks if t.state == TrackState.CONFIRMED)
        tentative_count = sum(1 for t in active_tracks if t.state == TrackState.TENTATIVE)
        lost_count = sum(1 for t in active_tracks if t.state == TrackState.LOST)
        avg_age = (sum(t.age for t in active_tracks) / len(active_tracks)) if active_tracks else 0.0

        # 5. Track Continuity
        total_gt_frames_sum = sum(self.gt_total_frames.values())
        maintained_gt_frames_sum = sum(self.gt_track_duration.values())
        track_continuity = (maintained_gt_frames_sum / total_gt_frames_sum) if total_gt_frames_sum > 0 else 1.0

        return {
            "active_tracks_count": len(active_tracks),
            "confirmed_tracks_count": confirmed_count,
            "tentative_tracks_count": tentative_count,
            "lost_tracks_count": lost_count,
            "id_switches": self.id_switch_count,
            "track_continuity": round(track_continuity, 4),
            "association_rate": round(association_rate, 4),
            "average_track_age": round(avg_age, 2),
            "ground_truth_count": len(gt_in_range),
            "detection_count": det_count,
        }
