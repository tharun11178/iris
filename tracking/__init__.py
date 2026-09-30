"""
IRIS Multi-Object Tracking Package (Phase 7).
"""

from tracking.track import Track, TrackState
from tracking.track_manager import TrackManager
from tracking.data_association import associate_detections_to_tracks
import tracking.config as config

__all__ = [
    "Track",
    "TrackState",
    "TrackManager",
    "associate_detections_to_tracks",
    "config",
]
