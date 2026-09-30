"""
IRIS Data Association Module (Phase 7).
Implements transparent baseline spatial distance data association with class filtering
and 1-to-1 greedy matching between active tracks and perceived detections.
"""

import math
from typing import List, Tuple, Set
from perception.detected_object import DetectedObject
from tracking.track import Track, TrackState
from tracking.config import MATCH_DISTANCE_THRESHOLD


def associate_detections_to_tracks(
    tracks: List[Track],
    detections: List[DetectedObject],
    max_distance: float = MATCH_DISTANCE_THRESHOLD,
) -> Tuple[List[Tuple[Track, DetectedObject]], List[Track], List[DetectedObject]]:
    """
    Associates perceived DetectedObjects with existing active Tracks using class-filtered Euclidean spatial distance.
    
    :param tracks: List of existing Track objects.
    :param detections: List of newly perceived DetectedObject instances.
    :param max_distance: Maximum allowable spatial distance in meters for association.
    :return: Tuple containing:
             - List of matched (Track, DetectedObject) pairs.
             - List of unmatched Track objects.
             - List of unmatched DetectedObject instances.
    """
    if not tracks:
        return [], [], list(detections)

    if not detections:
        active_unmatched_tracks = [t for t in tracks if t.state != TrackState.DELETED]
        return [], active_unmatched_tracks, []

    # 1. Collect candidate matches considering class-aware constraints and distance thresholds
    candidate_matches = []
    
    for t_idx, track in enumerate(tracks):
        # Ignore deleted tracks
        if track.state == TrackState.DELETED:
            continue

        tx, ty = track.current_position

        for d_idx, det in enumerate(detections):
            # Class-Aware Matching: Do not match completely different object classes
            if track.object_type != det.object_type:
                continue

            dx, dy = det.position
            dist = math.hypot(dx - tx, dy - ty)

            if dist <= max_distance:
                candidate_matches.append((dist, t_idx, d_idx))

    # 2. Sort candidate matches by distance ascending (greedy baseline optimization)
    candidate_matches.sort(key=lambda x: x[0])

    # 3. One-to-One Assignment
    assigned_track_indices: Set[int] = set()
    assigned_det_indices: Set[int] = set()
    matched_pairs: List[Tuple[Track, DetectedObject]] = []

    for dist, t_idx, d_idx in candidate_matches:
        if t_idx in assigned_track_indices or d_idx in assigned_det_indices:
            continue

        assigned_track_indices.add(t_idx)
        assigned_det_indices.add(d_idx)
        matched_pairs.append((tracks[t_idx], detections[d_idx]))

    # 4. Identify Unmatched Tracks and Detections
    unmatched_tracks: List[Track] = [
        tracks[t_idx]
        for t_idx, track in enumerate(tracks)
        if track.state != TrackState.DELETED and t_idx not in assigned_track_indices
    ]

    unmatched_detections: List[DetectedObject] = [
        detections[d_idx]
        for d_idx, det in enumerate(detections)
        if d_idx not in assigned_det_indices
    ]

    return matched_pairs, unmatched_tracks, unmatched_detections
