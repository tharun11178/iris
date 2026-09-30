"""
IRIS Track Object Representation (Phase 7).
Represents a persistent tracked object state over time, maintaining identity, position,
velocity, acceleration, and historical movement trail.
"""

import math
from enum import Enum
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from perception.object_classes import ObjectClass
from perception.detected_object import DetectedObject
from tracking.config import (
    MIN_CONFIRMATION_HITS,
    MAX_MISSED_FRAMES,
    MAX_HISTORY_LENGTH,
    VELOCITY_SMOOTHING_ALPHA,
    MIN_TRACK_CONFIDENCE,
)


class TrackState(Enum):
    """Lifecycle states of a Tracked Object."""
    TENTATIVE = "TENTATIVE"    # Newly initialized track awaiting sufficient observations
    CONFIRMED = "CONFIRMED"    # Confirmed persistent track with high confidence
    LOST = "LOST"              # Temporarily unobserved track (within MAX_MISSED_FRAMES)
    DELETED = "DELETED"        # Stale track past max allowed missed frames, to be removed


@dataclass
class Track:
    """
    Persistent state representation for a single tracked traffic participant over time.
    """
    track_id: str
    object_type: ObjectClass
    current_position: Tuple[float, float]
    previous_position: Optional[Tuple[float, float]] = None
    velocity: Tuple[float, float] = (0.0, 0.0)
    speed: float = 0.0
    acceleration: Optional[Tuple[float, float]] = None
    confidence: float = 1.0
    age: int = 1
    hits: int = 1
    missed_frames: int = 0
    state: TrackState = TrackState.TENTATIVE
    last_timestamp: Optional[float] = None
    history: List[Tuple[float, float]] = field(default_factory=list)
    width: float = 1.0
    length: float = 2.0
    height: Optional[float] = None
    heading: float = 0.0

    def __post_init__(self):
        """Initializes position history if empty."""
        if not self.history:
            self.history = [self.current_position]

    def update_with_detection(
        self,
        det: DetectedObject,
        dt: float,
        alpha: float = VELOCITY_SMOOTHING_ALPHA,
        min_hits: int = MIN_CONFIRMATION_HITS,
        max_history: int = MAX_HISTORY_LENGTH,
    ):
        """
        Updates track state when a matching detection observation is associated in the current frame.
        
        :param det: The associated DetectedObject instance.
        :param dt: Time elapsed in seconds since last update.
        :param alpha: Velocity exponential smoothing factor.
        :param min_hits: Minimum hits to confirm track.
        :param max_history: Maximum history trail length.
        """
        self.previous_position = self.current_position
        self.current_position = det.position
        
        # Append current position to position trail history
        self.history.append(self.current_position)
        if len(self.history) > max_history:
            self.history = self.history[-max_history:]

        # Estimate instantaneous raw velocity and apply smoothing
        if dt > 0.0 and self.previous_position is not None:
            raw_vx = (self.current_position[0] - self.previous_position[0]) / dt
            raw_vy = (self.current_position[1] - self.previous_position[1]) / dt

            # Velocity smoothing: v = alpha * v_raw + (1 - alpha) * v_prev
            if self.hits == 1 or (self.velocity[0] == 0.0 and self.velocity[1] == 0.0):
                smoothed_vx = raw_vx
                smoothed_vy = raw_vy
            else:
                smoothed_vx = alpha * raw_vx + (1.0 - alpha) * self.velocity[0]
                smoothed_vy = alpha * raw_vy + (1.0 - alpha) * self.velocity[1]

            # Estimate instantaneous acceleration if previous velocity exists
            prev_vx, prev_vy = self.velocity
            ax = (smoothed_vx - prev_vx) / dt
            ay = (smoothed_vy - prev_vy) / dt
            self.acceleration = (ax, ay)

            self.velocity = (smoothed_vx, smoothed_vy)
            self.speed = math.hypot(smoothed_vx, smoothed_vy)

        # Update physical bounding box attributes
        self.object_type = det.object_type
        self.width = det.width
        self.length = det.length
        self.height = det.height
        self.heading = det.heading
        self.confidence = det.confidence
        self.last_timestamp = det.timestamp

        # Update lifecycle statistics
        self.hits += 1
        self.age += 1
        self.missed_frames = 0

        # State transition logic
        if self.state == TrackState.TENTATIVE and self.hits >= min_hits:
            self.state = TrackState.CONFIRMED
        elif self.state == TrackState.LOST:
            self.state = TrackState.CONFIRMED

    def mark_missed(
        self,
        max_missed: int = MAX_MISSED_FRAMES,
        min_confidence: float = MIN_TRACK_CONFIDENCE,
    ):
        """
        Updates track state when no matching detection is associated in the current frame.
        
        :param max_missed: Maximum allowed missed frames threshold.
        :param min_confidence: Floor for confidence decay.
        """
        self.missed_frames += 1
        self.age += 1
        
        # Gradually decay confidence on missed observations
        self.confidence = max(min_confidence, self.confidence * 0.9)

        if self.missed_frames > max_missed:
            self.state = TrackState.DELETED
        elif self.state == TrackState.CONFIRMED:
            self.state = TrackState.LOST

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Track object into dictionary for logging, serialization, or WorldModel."""
        return {
            "track_id": self.track_id,
            "object_type": self.object_type.name,
            "position": self.current_position,
            "x": self.current_position[0],
            "y": self.current_position[1],
            "previous_position": self.previous_position,
            "velocity": self.velocity,
            "vx": self.velocity[0],
            "vy": self.velocity[1],
            "speed": self.speed,
            "acceleration": self.acceleration,
            "confidence": self.confidence,
            "age": self.age,
            "hits": self.hits,
            "missed_frames": self.missed_frames,
            "state": self.state.name,
            "last_timestamp": self.last_timestamp,
            "history": self.history,
            "width": self.width,
            "length": self.length,
            "height": self.height,
            "heading": self.heading,
        }
