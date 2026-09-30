"""
IRIS Safe Corridor Model (Phase 11).
Defines candidate drivable corridors and candidate paths evaluated by the Safe-Space Planner.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class SafeCorridor:
    """
    Represents a candidate safe corridor / candidate path through drivable negative space.
    """
    corridor_id: str
    name: str = ""
    centerline: List[Tuple[float, float]] = field(default_factory=list)  # World points (x, y)
    grid_cells: List[Tuple[int, int]] = field(default_factory=list)      # Grid cell indices (row, col)
    width: float = 0.0                      # Minimum bottleneck width in meters
    length: float = 0.0                     # Path length in meters
    min_clearance: float = 0.0              # Minimum clearance distance along path
    avg_clearance: float = 0.0              # Average clearance distance along path
    avg_risk: float = 0.0                   # Average spatial/future risk along path
    peak_risk: float = 0.0                  # Peak spatial/future risk along path
    risk_integral: float = 0.0              # Integrated future risk along path
    surface_cost: float = 0.0               # Road surface hazard cost penalty
    boundary_cost: float = 0.0              # Proximity to road boundary penalty
    smoothness_cost: float = 0.0            # Path geometric curvature / heading change cost
    clearance_cost: float = 0.0             # Inverse clearance penalty
    length_cost: float = 0.0                # Length penalty
    uncertainty_cost: float = 0.0           # Prediction uncertainty cost
    goal_cost: float = 0.0                  # Distance to goal penalty
    total_score: float = 999.0              # Final multi-objective weighted cost score
    is_valid: bool = True                   # Hard safety constraint compliance
    rejection_reason: str = ""              # Reason if candidate rejected by hard constraint

    def to_dict(self) -> Dict[str, Any]:
        """Returns structured dictionary summary of corridor metrics."""
        return {
            "corridor_id": self.corridor_id,
            "name": self.name,
            "length": round(self.length, 2),
            "min_clearance": round(self.min_clearance, 2),
            "avg_risk": round(self.avg_risk, 3),
            "peak_risk": round(self.peak_risk, 3),
            "surface_cost": round(self.surface_cost, 3),
            "boundary_cost": round(self.boundary_cost, 3),
            "smoothness_cost": round(self.smoothness_cost, 3),
            "total_score": round(self.total_score, 3),
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason,
        }
