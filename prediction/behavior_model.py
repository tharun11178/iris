"""
IRIS Behavior Model Package (Phase 8).
Defines behavior categories and class-specific motion profile heuristics for cars,
motorcycles, pedestrians, bicycles, cattle, trucks, and buses.
"""

from enum import Enum
from typing import Dict, Any, List, Tuple
from perception.object_classes import ObjectClass
from tracking.track import Track
from prediction.config import (
    CAR_MARGIN,
    TRUCK_MARGIN,
    MOTORCYCLE_MARGIN,
    PEDESTRIAN_MARGIN,
    CATTLE_MARGIN,
    BICYCLE_MARGIN,
    STOP_SPEED_THRESHOLD,
)


class BehaviorCategory(Enum):
    """Categorical motion behaviors of traffic participants."""
    FORWARD = "FORWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    SLOW_DOWN = "SLOW_DOWN"
    STOP = "STOP"
    LATERAL_SHIFT = "LATERAL_SHIFT"
    IRREGULAR = "IRREGULAR"


class BehaviorProfile:
    """
    Configurable behavior profile for an object class.
    """
    def __init__(
        self,
        preferred_model: str = "constant_velocity",
        lateral_margin: float = 0.5,
        longitudinal_margin: float = 0.5,
        supports_multi_hypothesis: bool = False,
        hypotheses_behaviors: List[BehaviorCategory] = None,
    ):
        self.preferred_model = preferred_model
        self.lateral_margin = lateral_margin
        self.longitudinal_margin = longitudinal_margin
        self.supports_multi_hypothesis = supports_multi_hypothesis
        self.hypotheses_behaviors = hypotheses_behaviors or [BehaviorCategory.FORWARD]


# Class-specific behavior profile registry for prototype simulation
BEHAVIOR_PROFILES: Dict[str, BehaviorProfile] = {
    "CAR": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=CAR_MARGIN,
        longitudinal_margin=0.5,
        supports_multi_hypothesis=False,
    ),
    "TRUCK": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=TRUCK_MARGIN,
        longitudinal_margin=0.8,
        supports_multi_hypothesis=False,
    ),
    "BUS": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=TRUCK_MARGIN,
        longitudinal_margin=0.8,
        supports_multi_hypothesis=False,
    ),
    "MOTORCYCLE": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=MOTORCYCLE_MARGIN,
        longitudinal_margin=0.5,
        supports_multi_hypothesis=False,
    ),
    "BICYCLE": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=BICYCLE_MARGIN,
        longitudinal_margin=0.5,
        supports_multi_hypothesis=False,
    ),
    "PEDESTRIAN": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=PEDESTRIAN_MARGIN,
        longitudinal_margin=0.6,
        supports_multi_hypothesis=False,
    ),
    "CATTLE": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=CATTLE_MARGIN,
        longitudinal_margin=0.8,
        supports_multi_hypothesis=True,
        hypotheses_behaviors=[BehaviorCategory.FORWARD, BehaviorCategory.TURN_LEFT, BehaviorCategory.TURN_RIGHT],
    ),
    "OTHER": BehaviorProfile(
        preferred_model="constant_velocity",
        lateral_margin=0.8,
        longitudinal_margin=0.8,
        supports_multi_hypothesis=False,
    ),
}


def get_behavior_profile(object_type: Any) -> BehaviorProfile:
    """Returns BehaviorProfile for given ObjectClass or string."""
    type_str = object_type.name if hasattr(object_type, "name") else str(object_type)
    return BEHAVIOR_PROFILES.get(type_str, BEHAVIOR_PROFILES["OTHER"])


def classify_motion_pattern(track: Track) -> BehaviorCategory:
    """
    Analyzes track speed and recent position history to identify simple motion pattern.
    
    :param track: Active Track object.
    :return: Categorical BehaviorCategory.
    """
    if track.speed < STOP_SPEED_THRESHOLD:
        return BehaviorCategory.STOP

    type_str = track.object_type.name if hasattr(track.object_type, "name") else str(track.object_type)
    if type_str == "CATTLE":
        return BehaviorCategory.IRREGULAR

    # Check lateral drift in history
    if len(track.history) >= 3:
        y_coords = [p[1] for p in track.history[-3:]]
        y_drift = max(y_coords) - min(y_coords)
        if y_drift > 0.8:
            return BehaviorCategory.LATERAL_SHIFT

    return BehaviorCategory.FORWARD
