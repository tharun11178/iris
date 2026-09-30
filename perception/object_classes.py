"""
IRIS Object Class Definitions (Phase 6).
Provides structured Enum definitions for traffic perception object classification
and bidirectional conversion mapping from simulation actor types.
"""

from enum import Enum, auto
from typing import Union, Any


class ObjectClass(Enum):
    """
    Standard object taxonomy for IRIS Traffic Perception.
    Minimum mandatory classes: CAR, MOTORCYCLE, PEDESTRIAN, BICYCLE, CATTLE, TRUCK, BUS, OTHER.
    """
    CAR = auto()
    MOTORCYCLE = auto()
    PEDESTRIAN = auto()
    BICYCLE = auto()
    CATTLE = auto()
    TRUCK = auto()
    BUS = auto()
    OTHER = auto()

    @classmethod
    def from_actor_type(cls, actor_type: Any) -> "ObjectClass":
        """
        Maps a simulation ActorType or string name to standard ObjectClass.
        """
        type_str = actor_type.name if hasattr(actor_type, "name") else str(actor_type).upper()
        
        if type_str == "CAR":
            return cls.CAR
        elif type_str == "MOTORCYCLE":
            return cls.MOTORCYCLE
        elif type_str == "PEDESTRIAN":
            return cls.PEDESTRIAN
        elif type_str == "BICYCLE":
            return cls.BICYCLE
        elif type_str == "CATTLE":
            return cls.CATTLE
        elif type_str == "TRUCK":
            return cls.TRUCK
        elif type_str == "BUS":
            return cls.BUS
        elif type_str in ("BUS_TRUCK", "HEAVY_VEHICLE"):
            # Default to BUS or TRUCK depending on representation
            return cls.TRUCK
        elif type_str in ("AUTO_RICKSHAW", "PUSHCART", "OTHER", "EGO"):
            return cls.OTHER
        else:
            return cls.OTHER

    def __str__(self) -> str:
        return self.name
