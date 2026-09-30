"""
IRIS Surface Hazard Data Model (Phase 5)
Defines structured representation for road surface hazards, hazard types,
traversability states, and property accessors.
"""

from enum import Enum, auto
from typing import Tuple, Optional, Dict, Any


class SurfaceHazardType(Enum):
    POTHOLE = auto()
    WATERLOGGING = auto()
    DEPRESSION = auto()
    RAISED_SURFACE = auto()
    UNEVEN_SURFACE = auto()
    DEBRIS = auto()
    CONSTRUCTION = auto()


class TraversabilityState(Enum):
    SAFE = auto()             # Normal drivable road condition
    CAUTION = auto()          # Traversable with minor speed reduction / caution
    RISKY = auto()            # Traversable with high caution & potential vehicle strain
    NON_TRAVERSABLE = auto()  # Physically impassable / severe damage risk


class SurfaceHazard:
    """
    Structured model for discrete road surface hazards.
    """

    def __init__(
        self,
        hazard_id: str,
        hazard_type: SurfaceHazardType,
        position: Tuple[float, float],
        length: float,
        width: float,
        depth: Optional[float] = None,
        height: Optional[float] = None,
        roughness: Optional[float] = None,
        severity: float = 0.5,
        confidence: float = 0.9,
        underlying_surface_known: bool = True,
        traversability: TraversabilityState = TraversabilityState.CAUTION,
        surface_risk: float = 0.5,
        description: str = "",
    ):
        self.hazard_id: str = str(hazard_id)
        self.hazard_type: SurfaceHazardType = hazard_type
        self.position: Tuple[float, float] = position  # (x, y) world meters
        self.length: float = max(0.1, float(length))
        self.width: float = max(0.1, float(width))
        self.depth: Optional[float] = float(depth) if depth is not None else None
        self.height: Optional[float] = float(height) if height is not None else None
        self.roughness: Optional[float] = float(roughness) if roughness is not None else None
        self.severity: float = float(min(1.0, max(0.0, severity)))
        self.confidence: float = float(min(1.0, max(0.0, confidence)))
        self.underlying_surface_known: bool = underlying_surface_known
        self.traversability: TraversabilityState = traversability
        self.surface_risk: float = float(min(1.0, max(0.0, surface_risk)))
        self.description: str = description if description else f"{hazard_type.name} ({hazard_id})"

    @property
    def x(self) -> float:
        return self.position[0]

    @property
    def y(self) -> float:
        return self.position[1]

    @property
    def affected_area(self) -> float:
        """Returns physical surface footprint area in square meters."""
        return self.length * self.width

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Returns axis-aligned bounding box (min_x, max_x, min_y, max_y) in world meters."""
        half_l = self.length / 2.0
        half_w = self.width / 2.0
        return (self.x - half_l, self.x + half_l, self.y - half_w, self.y + half_w)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes hazard attributes into dictionary format."""
        return {
            "hazard_id": self.hazard_id,
            "hazard_type": self.hazard_type.name,
            "position": self.position,
            "length": self.length,
            "width": self.width,
            "depth": self.depth,
            "height": self.height,
            "roughness": self.roughness,
            "severity": self.severity,
            "confidence": self.confidence,
            "underlying_surface_known": self.underlying_surface_known,
            "traversability": self.traversability.name,
            "surface_risk": self.surface_risk,
            "affected_area": self.affected_area,
            "description": self.description,
        }
