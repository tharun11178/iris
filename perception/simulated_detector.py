"""
IRIS Simulated Object Detector (Phase 6).
Provides a controlled ground-truth synthetic perception source that converts simulation
traffic actors into standardized DetectedObject observations within a configurable sensor range,
supporting optional perceptual noise, position error, and missed detections.
"""

import math
import random
from typing import List, Any, Optional
import numpy as np

from perception.object_detector import ObjectDetector
from perception.detected_object import DetectedObject
from perception.object_classes import ObjectClass
from perception.config import (
    DETECTION_RANGE,
    USE_SIMULATED_NOISE,
    POSITION_NOISE_STD,
    MISS_PROBABILITY,
    CONFIDENCE_RANGE,
    RANDOM_SEED,
)
from world.coordinate_system import CoordinateConverter


class SimulatedDetector(ObjectDetector):
    """
    Ground-truth based synthetic perception detector for validating perception pipeline.
    """

    def __init__(
        self,
        detection_range: float = DETECTION_RANGE,
        use_noise: bool = USE_SIMULATED_NOISE,
        position_noise_std: float = POSITION_NOISE_STD,
        miss_probability: float = MISS_PROBABILITY,
        confidence_range: tuple = CONFIDENCE_RANGE,
        seed: Optional[int] = RANDOM_SEED,
        converter: Optional[CoordinateConverter] = None,
    ):
        self.detection_range = detection_range
        self.use_noise = use_noise
        self.position_noise_std = position_noise_std
        self.miss_probability = miss_probability
        self.confidence_range = confidence_range
        self.seed = seed
        self.rng = random.Random(seed) if seed is not None else random.Random()
        self.converter = converter if converter is not None else CoordinateConverter()

    def set_seed(self, seed: int):
        """Sets deterministic random seed for reproducible testing."""
        self.seed = seed
        self.rng = random.Random(seed)

    def detect(self, sensor_input: Any) -> List[DetectedObject]:
        """
        Processes simulation environment state into standardized DetectedObject observations.
        
        :param sensor_input: SimulationEnvironment instance or environment dictionary.
        :return: List[DetectedObject] within sensor range.
        """
        if sensor_input is None:
            return []

        # Handle both SimulationEnvironment object and dict input format
        if hasattr(sensor_input, "ego_vehicle") and hasattr(sensor_input, "traffic_actors"):
            ego = sensor_input.ego_vehicle
            actors = sensor_input.traffic_actors
            sim_time = getattr(sensor_input, "sim_time", 0.0)
        elif isinstance(sensor_input, dict):
            ego = sensor_input.get("ego_vehicle")
            actors = sensor_input.get("traffic_actors", [])
            sim_time = sensor_input.get("sim_time", 0.0)
        else:
            return []

        # Extract Ego position in World frame
        if hasattr(ego, "x") and hasattr(ego, "y"):
            ego_wx, ego_wy = self.converter.sim_to_world(ego.x, ego.y)
        elif isinstance(ego, dict):
            ego_wx, ego_wy = self.converter.sim_to_world(ego.get("x", 0.0), ego.get("y", 0.0))
        else:
            ego_wx, ego_wy = 0.0, 0.0

        detections: List[DetectedObject] = []

        for actor in actors:
            # Extract actor attributes safely
            if hasattr(actor, "actor_id"):
                actor_id = f"OBJ_{actor.actor_id}"
                actor_type_raw = actor.actor_type
                sim_x, sim_y = actor.x, actor.y
                heading = getattr(actor, "heading", 0.0)
                velocity_mag = getattr(actor, "velocity", 0.0)
                length = getattr(actor, "length", 2.0)
                width = getattr(actor, "width", 1.0)
            elif isinstance(actor, dict):
                actor_id = f"OBJ_{actor.get('id', '0')}"
                actor_type_raw = actor.get("type", "CAR")
                sim_x, sim_y = actor.get("x", 0.0), actor.get("y", 0.0)
                heading = actor.get("heading", 0.0)
                velocity_mag = actor.get("velocity", 0.0)
                length = actor.get("length", 2.0)
                width = actor.get("width", 1.0)
            else:
                continue

            # Convert to World coordinates
            wx, wy = self.converter.sim_to_world(sim_x, sim_y)

            # Check 2D Euclidean distance to Ego vehicle
            dist = math.hypot(wx - ego_wx, wy - ego_wy)
            if dist > self.detection_range:
                continue

            # Apply configurable perception noise if enabled
            if self.use_noise:
                # 1. Missed Detection check
                if self.rng.random() < self.miss_probability:
                    continue

                # 2. Position noise addition
                wx += self.rng.gauss(0.0, self.position_noise_std)
                wy += self.rng.gauss(0.0, self.position_noise_std)

                # 3. Confidence score variation
                confidence = float(self.rng.uniform(self.confidence_range[0], self.confidence_range[1]))
            else:
                confidence = 0.95

            # Map to ObjectClass Enum
            obj_class = ObjectClass.from_actor_type(actor_type_raw)

            # Instantaneous velocity vector (vx, vy)
            vx = velocity_mag * math.cos(heading)
            vy = velocity_mag * math.sin(heading)

            detection = DetectedObject(
                object_id=actor_id,
                object_type=obj_class,
                position=(wx, wy),
                width=width,
                length=length,
                confidence=confidence,
                source="simulated_detector",
                timestamp=sim_time,
                velocity=(vx, vy),
                is_dynamic=True,
                heading=heading,
            )
            detections.append(detection)

        return detections
