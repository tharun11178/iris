"""
IRIS Grid Cell Data Structure (Phase 2)
Defines CellState enumeration and GridCell container class holding spatial, state,
and metadata attributes for each grid cell in the World Model.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional


class CellState(Enum):
    """
    Occupancy & surface state of a grid cell in the IRIS World Model.
    """
    FREE = auto()             # Clear drivable road surface
    OCCUPIED = auto()         # Blocked by static obstacle / structure
    POTHOLE = auto()          # Road surface pothole hazard
    WATER = auto()            # Waterlogged surface (depth uncertainty)
    UNEVEN_TERRAIN = auto()   # Rough / degraded surface
    RAISED = auto()           # Speed breaker / elevated section
    ROAD_BOUNDARY = auto()    # Edge curb / asphalt boundary mark
    OUTSIDE_ROAD = auto()     # Non-drivable shoulder / terrain outside road
    VEHICLE = auto()          # Ego vehicle current footprint
    DYNAMIC_OBJECT = auto()   # Moving traffic actor footprint (Auto, Cow, Pedestrian, etc.)


@dataclass
class GridCell:
    """
    Represents a single discrete spatial unit in the 2D occupancy grid.
    """
    row: int
    col: int
    x_world: float
    y_world: float
    state: CellState = CellState.FREE
    is_drivable: bool = True
    hazard_type: str = "NONE"
    occupancy: float = 0.0          # 0.0 (empty) to 1.0 (fully occupied)
    is_dynamic: bool = False        # True for dynamic actors, False for static
    severity: float = 0.0           # 0.0 (minor) to 1.0 (severe)
    confidence: float = 1.0         # Perception confidence / ground truth assurance
    entity_id: Optional[str] = None # Associated actor/hazard identifier

    def reset(self, default_state: CellState = CellState.FREE, default_drivable: bool = True):
        """
        Resets cell state back to default baseline.
        """
        self.state = default_state
        self.is_drivable = default_drivable
        self.hazard_type = "NONE"
        self.occupancy = 0.0
        self.is_dynamic = False
        self.severity = 0.0
        self.confidence = 1.0
        self.entity_id = None
