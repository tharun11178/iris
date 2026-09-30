"""
IRIS Perception Manager (Phase 6).
Central manager responsible for receiving sensor input, invoking configured detectors,
validating and filtering detections, and returning standardized DetectedObject lists.
"""

import math
from typing import List, Optional, Any
from perception.object_detector import ObjectDetector
from perception.simulated_detector import SimulatedDetector
from perception.detected_object import DetectedObject
from perception.object_classes import ObjectClass
from perception.config import MIN_CONFIDENCE, MAX_CONFIDENCE


class PerceptionManager:
    """
    Manages perception execution and validation pipeline.
    """

    def __init__(
        self,
        detector: Optional[ObjectDetector] = None,
        min_confidence: float = MIN_CONFIDENCE,
    ):
        self.detector = detector if detector is not None else SimulatedDetector()
        self.min_confidence = min_confidence
        self.last_detections: List[DetectedObject] = []

    def set_detector(self, detector: ObjectDetector):
        """Allows dynamically swapping the detector (e.g. Simulated -> Future Camera Detector)."""
        self.detector = detector

    def process(self, sensor_input: Any) -> List[DetectedObject]:
        """
        Executes perception pipeline: receives sensor input, calls detector, validates detections,
        filters invalid items, and returns clean standardized DetectedObjects.
        
        :param sensor_input: Raw sensor input or SimulationEnvironment instance.
        :return: Validated List[DetectedObject].
        """
        if self.detector is None or sensor_input is None:
            self.last_detections = []
            return []

        # 1. Obtain raw detections from detector
        raw_detections = self.detector.detect(sensor_input)

        # 2. Filter & Validate detections safely
        validated_detections: List[DetectedObject] = []
        for det in raw_detections:
            if self.validate_detection(det):
                validated_detections.append(det)

        self.last_detections = validated_detections
        return validated_detections

    def validate_detection(self, det: Any) -> bool:
        """
        Validates a single detection against sanity bounds and format requirements.
        Rejects malformed detections safely without crashing.
        
        Validation rules:
        - Must be instance of DetectedObject
        - object_id must exist and be non-empty string
        - object_type must be a valid ObjectClass Enum
        - confidence must be finite number in [0.0, 1.0] and >= min_confidence
        - position must be tuple/list of 2 finite numeric coordinates
        - width and length must be non-negative finite numbers
        - timestamp must be finite non-negative number
        """
        if not isinstance(det, DetectedObject):
            return False

        # Object ID check
        if not det.object_id or not isinstance(det.object_id, str):
            return False

        # Object Class check
        if not isinstance(det.object_type, ObjectClass):
            return False

        # Confidence check
        if det.confidence is None or not math.isfinite(det.confidence):
            return False
        if not (0.0 <= det.confidence <= MAX_CONFIDENCE) or det.confidence < self.min_confidence:
            return False

        # Position check
        if not det.position or len(det.position) != 2:
            return False
        x, y = det.position
        if x is None or y is None or not (math.isfinite(x) and math.isfinite(y)):
            return False

        # Dimensions check
        if det.width is None or det.length is None:
            return False
        if not (math.isfinite(det.width) and math.isfinite(det.length)):
            return False
        if det.width < 0.0 or det.length < 0.0:
            return False

        # Timestamp check
        if det.timestamp is None or not math.isfinite(det.timestamp) or det.timestamp < 0.0:
            return False

        return True
