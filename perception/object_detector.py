"""
IRIS Object Detector Generic Interface (Phase 6).
Defines standard interface for perception object detectors (Simulated, Camera, LiDAR, Radar, etc.).
"""

from abc import ABC, abstractmethod
from typing import List, Any
from perception.detected_object import DetectedObject


class ObjectDetector(ABC):
    """
    Abstract interface for all IRIS object detection models and sensor drivers.
    Decouples sensor algorithms (Simulated, YOLO, LiDAR PointPillars, Radar) from WorldModel and Risk Engine.
    """

    @abstractmethod
    def detect(self, sensor_input: Any) -> List[DetectedObject]:
        """
        Executes perception detection on sensor input / simulation frame.
        
        :param sensor_input: Raw sensor payload or SimulationEnvironment instance.
        :return: List of standardized DetectedObject instances.
        """
        pass
