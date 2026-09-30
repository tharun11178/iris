"""
IRIS Detected Object Representation (Phase 6).
Represents a standardized perception observation emitted by sensor detectors.
"""

from dataclasses import dataclass
from typing import Tuple, Optional
from perception.object_classes import ObjectClass


@dataclass
class DetectedObject:
    """
    Standardized traffic perception observation output.
    
    Attributes:
        object_id: Unique string identifier for the observation.
        object_type: Classified ObjectClass (CAR, MOTORCYCLE, PEDESTRIAN, etc.).
        position: World coordinates (x_meters, y_meters).
        width: Physical width in meters.
        length: Physical length in meters.
        confidence: Perception detection confidence [0.0, 1.0].
        source: Detector source name (e.g. "simulation", "camera", "lidar").
        timestamp: Simulation timestamp (seconds) when detected.
        height: Optional physical height in meters.
        velocity: Optional instantaneous velocity tuple (vx, vy) in m/s.
        is_dynamic: Whether the object is dynamic (moving or movable) vs static.
        heading: Orientation yaw angle in radians (0 = along +X world direction).
    """
    object_id: str
    object_type: ObjectClass
    position: Tuple[float, float]
    width: float
    length: float
    confidence: float
    source: str
    timestamp: float
    height: Optional[float] = None
    velocity: Optional[Tuple[float, float]] = None
    is_dynamic: bool = True
    heading: float = 0.0

    def to_dict(self) -> dict:
        """Serializes DetectedObject into a dictionary representation."""
        return {
            "object_id": self.object_id,
            "object_type": self.object_type.name,
            "position": self.position,
            "x": self.position[0],
            "y": self.position[1],
            "width": self.width,
            "length": self.length,
            "height": self.height,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "velocity": self.velocity,
            "vx": self.velocity[0] if self.velocity else 0.0,
            "vy": self.velocity[1] if self.velocity else 0.0,
            "is_dynamic": self.is_dynamic,
            "heading": self.heading,
        }
