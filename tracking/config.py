"""
IRIS Multi-Object Tracking Configuration (Phase 7).
Centralized configuration thresholds and hyperparameters for position-based tracking baseline.
"""

# Spatial distance threshold (in meters) for matching detections to existing tracks
MATCH_DISTANCE_THRESHOLD: float = 3.0

# Number of consecutive matching frames required to promote a TENTATIVE track to CONFIRMED
MIN_CONFIRMATION_HITS: int = 3

# Maximum consecutive missed frames before a track is marked as DELETED
MAX_MISSED_FRAMES: int = 5

# Maximum number of historical positions stored for track trail visualization & future motion prediction
MAX_HISTORY_LENGTH: int = 20

# Exponential smoothing factor for velocity estimation: v_smoothed = alpha * v_raw + (1 - alpha) * v_prev
VELOCITY_SMOOTHING_ALPHA: float = 0.6

# Minimum floor for track confidence decay
MIN_TRACK_CONFIDENCE: float = 0.1

# Enable detailed tracking debug logs and overlays
TRACK_DEBUG: bool = True
