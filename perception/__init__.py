"""
IRIS Traffic Perception Package (Phase 6).
Provides object classification, observation models, detectors, perception manager, and coordinate mapping.
"""

from perception.object_classes import ObjectClass
from perception.detected_object import DetectedObject
from perception.object_detector import ObjectDetector
from perception.simulated_detector import SimulatedDetector
from perception.coordinate_mapper import CoordinateMapper
from perception.perception_manager import PerceptionManager

__all__ = [
    "ObjectClass",
    "DetectedObject",
    "ObjectDetector",
    "SimulatedDetector",
    "CoordinateMapper",
    "PerceptionManager",
]
