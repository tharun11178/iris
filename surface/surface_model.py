"""
IRIS Surface Model Facade (Phase 5)
Central manager for road surface hazards, spatial queries, multi-hazard overlap aggregation,
traversability checking, and surface risk evaluation.
"""

import math
from typing import List, Dict, Tuple, Optional, Any
from surface.surface_hazard import SurfaceHazard, SurfaceHazardType, TraversabilityState
from surface.surface_geometry import SurfaceGeometry
from surface.surface_classifier import SurfaceClassifier
from surface.config import SURFACE_INFLUENCE_RADII
from world.coordinate_system import CoordinateConverter


class SurfaceModel:
    """
    Central spatial Surface Model facade.
    Stores discrete SurfaceHazard instances and provides clean query APIs for WorldModel & RiskEngine.
    """

    def __init__(self):
        self._hazards: Dict[str, SurfaceHazard] = {}

    def get_hazards(self) -> List[SurfaceHazard]:
        """Returns list of all active surface hazards."""
        return list(self._hazards.values())

    def get_hazard(self, hazard_id: str) -> Optional[SurfaceHazard]:
        """Returns hazard by ID or None if not found."""
        return self._hazards.get(str(hazard_id), None)

    def add_hazard(self, hazard: SurfaceHazard) -> SurfaceHazard:
        """
        Adds or updates a SurfaceHazard in the surface model.
        Automatically runs SurfaceClassifier to compute severity, traversability, and surface_risk if default.
        """
        h_kwargs = {
            "length": hazard.length,
            "width": hazard.width,
            "depth": hazard.depth,
            "height": hazard.height,
            "roughness": hazard.roughness,
            "underlying_surface_known": hazard.underlying_surface_known,
        }

        calc_sev = SurfaceClassifier.calculate_severity(hazard.hazard_type, severity=hazard.severity, **h_kwargs)
        hazard.severity = calc_sev

        calc_trav = SurfaceClassifier.classify_traversability(hazard.hazard_type, calc_sev, **h_kwargs)
        hazard.traversability = calc_trav

        calc_risk = SurfaceClassifier.calculate_surface_risk(
            hazard.hazard_type, calc_sev, hazard.confidence, **h_kwargs
        )
        hazard.surface_risk = calc_risk

        self._hazards[hazard.hazard_id] = hazard
        return hazard

    def remove_hazard(self, hazard_id: str) -> bool:
        """Removes hazard by ID. Returns True if removed, False if not found."""
        h_id_str = str(hazard_id)
        if h_id_str in self._hazards:
            del self._hazards[h_id_str]
            return True
        return False

    def clear(self):
        """Clears all surface hazards."""
        self._hazards.clear()

    def get_hazards_at(self, x: float, y: float) -> List[SurfaceHazard]:
        """
        Returns list of all SurfaceHazard instances containing world point (x, y).
        """
        matching = []
        for hazard in self._hazards.values():
            if SurfaceGeometry.is_point_inside(hazard, x, y):
                matching.append(hazard)
        return matching

    def get_affected_cells(
        self,
        hazard_id: str,
        converter: CoordinateConverter,
        influence_radius: Optional[float] = None,
    ) -> List[Tuple[int, int]]:
        """
        Returns list of grid cell (row, col) tuples affected by specified hazard.
        """
        hazard = self.get_hazard(hazard_id)
        if hazard is None:
            return []

        rad = influence_radius
        if rad is None:
            rad = SURFACE_INFLUENCE_RADII.get(hazard.hazard_type.name, 1.5)

        return SurfaceGeometry.get_affected_grid_cells(hazard, converter, rad)

    def get_surface_risk(self, x: float, y: float) -> float:
        """
        Returns aggregated surface risk at world point (x, y).
        Handles multi-hazard overlap using probabilistic accumulation: 1 - prod(1 - r_i).
        Also accounts for proximity influence radii.
        """
        if not self._hazards:
            return 0.0

        one_minus_risk = 1.0

        for hazard in self._hazards.values():
            rad = SURFACE_INFLUENCE_RADII.get(hazard.hazard_type.name, 1.5)
            dist = SurfaceGeometry.distance_to_hazard(hazard, x, y)

            if SurfaceGeometry.is_point_inside(hazard, x, y):
                h_risk = hazard.surface_risk
            elif dist <= rad:
                # Spatial linear decay across influence radius
                spatial_decay = max(0.0, 1.0 - (dist / rad))
                h_risk = hazard.surface_risk * 0.5 * spatial_decay
            else:
                h_risk = 0.0

            if h_risk > 0.0:
                one_minus_risk *= (1.0 - h_risk)

        return float(min(1.0, max(0.0, 1.0 - one_minus_risk)))

    def is_surface_traversable(self, x: float, y: float) -> bool:
        """
        Returns True if the road surface at world point (x, y) is physically traversable.
        Returns False if ANY overlapping hazard at (x, y) is NON_TRAVERSABLE.
        Note: Risk and Traversability are evaluated separately.
        """
        hazards = self.get_hazards_at(x, y)
        for h in hazards:
            if h.traversability == TraversabilityState.NON_TRAVERSABLE:
                return False
        return True

    def get_surface_severity(self, x: float, y: float) -> float:
        """
        Returns maximum hazard severity at world point (x, y).
        """
        hazards = self.get_hazards_at(x, y)
        if not hazards:
            return 0.0
        return max(h.severity for h in hazards)

    def get_surface_confidence(self, x: float, y: float) -> float:
        """
        Returns average hazard confidence at world point (x, y). Default 1.0 if clear.
        """
        hazards = self.get_hazards_at(x, y)
        if not hazards:
            return 1.0
        return sum(h.confidence for h in hazards) / len(hazards)
