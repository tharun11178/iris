"""
IRIS Track Manager (Phase 7).
Central tracking manager that receives perception detections, performs spatial data association,
maintains persistent track lifecycle, estimates velocity/acceleration, creates new tracks,
and handles track confirmation and deletion.
"""

from typing import List, Optional, Dict, Any
from perception.detected_object import DetectedObject
from tracking.track import Track, TrackState
from tracking.data_association import associate_detections_to_tracks
from tracking.config import (
    MATCH_DISTANCE_THRESHOLD,
    MIN_CONFIRMATION_HITS,
    MAX_MISSED_FRAMES,
    MAX_HISTORY_LENGTH,
    VELOCITY_SMOOTHING_ALPHA,
    MIN_TRACK_CONFIDENCE,
)


class TrackManager:
    """
    Manages multi-object tracking lifecycle and persistent track identity.
    """

    def __init__(
        self,
        match_distance_threshold: float = MATCH_DISTANCE_THRESHOLD,
        min_confirmation_hits: int = MIN_CONFIRMATION_HITS,
        max_missed_frames: int = MAX_MISSED_FRAMES,
        max_history_length: int = MAX_HISTORY_LENGTH,
        velocity_smoothing_alpha: float = VELOCITY_SMOOTHING_ALPHA,
    ):
        self.match_distance_threshold = match_distance_threshold
        self.min_confirmation_hits = min_confirmation_hits
        self.max_missed_frames = max_missed_frames
        self.max_history_length = max_history_length
        self.velocity_smoothing_alpha = velocity_smoothing_alpha

        self.tracks: List[Track] = []
        self.next_track_id_counter: int = 1

        # Counters for metrics tracking
        self.total_tracks_created: int = 0
        self.total_tracks_deleted: int = 0

    def generate_track_id(self) -> str:
        """Helper method to generate formatted stable track ID string."""
        track_id = f"TRACK_{self.next_track_id_counter:03d}"
        self.next_track_id_counter += 1
        return track_id

    def update(
        self,
        detections: List[DetectedObject],
        timestamp: float,
    ) -> List[Track]:
        """
        Executes frame-level tracking update pipeline:
        1. Perform spatial data association between existing active tracks and current detections.
        2. Update matched tracks with new position, velocity, timestamp, and history.
        3. Handle missed tracks (decay confidence, mark LOST or DELETED).
        4. Create new TENTATIVE tracks for unassociated detections with persistent track IDs.
        5. Purge DELETED tracks.
        6. Return active non-deleted tracks.
        
        :param detections: List of perceived DetectedObjects from perception layer.
        :param timestamp: Current simulation timestamp in seconds.
        :return: List of active Track objects.
        """
        active_tracks = [t for t in self.tracks if t.state != TrackState.DELETED]

        # 1. Spatial Data Association
        matches, unmatched_tracks, unmatched_detections = associate_detections_to_tracks(
            active_tracks,
            detections,
            max_distance=self.match_distance_threshold,
        )

        # 2. Update Matched Tracks
        for track, det in matches:
            det_ts = det.timestamp if (det.timestamp is not None and det.timestamp >= 0.0) else timestamp
            dt = det_ts - track.last_timestamp if track.last_timestamp is not None else 0.05
            if dt <= 0.0:
                dt = 0.05  # Default nominal frame step if timestamp is identical or non-increasing

            track.update_with_detection(
                det=det,
                dt=dt,
                alpha=self.velocity_smoothing_alpha,
                min_hits=self.min_confirmation_hits,
                max_history=self.max_history_length,
            )

        # 3. Handle Unmatched Tracks
        for track in unmatched_tracks:
            prev_state = track.state
            track.mark_missed(
                max_missed=self.max_missed_frames,
                min_confidence=MIN_TRACK_CONFIDENCE,
            )
            if track.state == TrackState.DELETED and prev_state != TrackState.DELETED:
                self.total_tracks_deleted += 1

        # 4. Create New Tracks for Unmatched Detections
        for det in unmatched_detections:
            new_id = f"TRACK_{self.next_track_id_counter:03d}"
            self.next_track_id_counter += 1
            self.total_tracks_created += 1

            det_ts = det.timestamp if (det.timestamp is not None and det.timestamp >= 0.0) else timestamp

            new_track = Track(
                track_id=new_id,
                object_type=det.object_type,
                current_position=det.position,
                confidence=det.confidence,
                last_timestamp=det_ts,
                width=det.width,
                length=det.length,
                height=det.height,
                heading=det.heading,
                state=TrackState.TENTATIVE,
                hits=1,
                age=1,
                missed_frames=0,
            )
            # Add initial position to history trail
            new_track.history = [det.position]

            # If MIN_CONFIRMATION_HITS is 1, immediately confirm track
            if self.min_confirmation_hits <= 1:
                new_track.state = TrackState.CONFIRMED

            self.tracks.append(new_track)

        # 5. Filter and return active tracks (non-deleted)
        return self.get_active_tracks()

    def get_active_tracks(self) -> List[Track]:
        """Returns list of all active non-deleted tracks (TENTATIVE, CONFIRMED, LOST)."""
        return [t for t in self.tracks if t.state != TrackState.DELETED]

    def get_confirmed_tracks(self) -> List[Track]:
        """Returns list of confirmed active tracks."""
        return [t for t in self.tracks if t.state == TrackState.CONFIRMED]

    def reset(self):
        """Resets tracking manager state and counters."""
        self.tracks.clear()
        self.next_track_id_counter = 1
        self.total_tracks_created = 0
        self.total_tracks_deleted = 0

    def get_summary(self) -> Dict[str, Any]:
        """Returns diagnostic dictionary summary of track status."""
        active = self.get_active_tracks()
        confirmed = self.get_confirmed_tracks()
        tentative = [t for t in active if t.state == TrackState.TENTATIVE]
        lost = [t for t in active if t.state == TrackState.LOST]

        return {
            "total_active": len(active),
            "confirmed_count": len(confirmed),
            "tentative_count": len(tentative),
            "lost_count": len(lost),
            "total_created": self.total_tracks_created,
            "total_deleted": self.total_tracks_deleted,
        }
