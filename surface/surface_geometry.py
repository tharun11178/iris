"""
IRIS Surface Geometry Engine (Phase 5)
Provides 2D spatial geometry operations for road surface hazards, including
point-containment, edge distance, bounding box inflation, overlap checks,
and grid cell rasterization mapping using Phase 2 CoordinateConverter.
"""

import math
from typing import Tuple, List, Optional
from surface.surface_hazard import SurfaceHazard
from world.coordinate_system import CoordinateConverter


class SurfaceGeometry:
    """
    Utility class for 2D surface hazard geometry calculations in world meters.
    """

    @staticmethod
    def is_point_inside(hazard: SurfaceHazard, x: float, y: float) -> bool:
        """
        Checks if world coordinate (x, y) is inside the hazard bounding footprint.
        """
        min_x, max_x, min_y, max_y = hazard.get_bounding_box()
        return min_x <= x <= max_x and min_y <= y <= max_y

    @staticmethod
    def distance_to_hazard(hazard: SurfaceHazard, x: float, y: float) -> float:
        """
        Calculates shortest distance from world point (x, y) to hazard boundary.
        Returns 0.0 if point is inside the hazard footprint.
        """
        min_x, max_x, min_y, max_y = hazard.get_bounding_box()

        dx = max(0.0, min_x - x, x - max_x)
        dy = max(0.0, min_y - y, y - max_y)

        return math.hypot(dx, dy)

    @staticmethod
    def check_hazard_overlap(hazard1: SurfaceHazard, hazard2: SurfaceHazard) -> bool:
        """
        Checks if two surface hazard bounding boxes overlap in world meters.
        """
        min_x1, max_x1, min_y1, max_y1 = hazard1.get_bounding_box()
        min_x2, max_x2, min_y2, max_y2 = hazard2.get_bounding_box()

        return not (max_x1 < min_x2 or min_x1 > max_x2 or max_y1 < min_y2 or min_y1 > max_y2)

    @staticmethod
    def get_inflated_bounding_box(hazard: SurfaceHazard, influence_radius: float = 0.0) -> Tuple[float, float, float, float]:
        """
        Returns bounding box expanded by influence_radius meters in all directions.
        """
        min_x, max_x, min_y, max_y = hazard.get_bounding_box()
        r = max(0.0, influence_radius)
        return (min_x - r, max_x + r, min_y - r, max_y + r)

    @staticmethod
    def get_affected_grid_cells(
        hazard: SurfaceHazard,
        converter: CoordinateConverter,
        influence_radius: float = 0.0,
    ) -> List[Tuple[int, int]]:
        """
        Converts hazard spatial footprint (plus optional influence margin) to grid cell (row, col) indices.
        """
        min_x, max_x, min_y, max_y = SurfaceGeometry.get_inflated_bounding_box(hazard, influence_radius)

        r_min, c_min = converter.world_to_grid(min_x, min_y)
        r_max, c_max = converter.world_to_grid(max_x, max_y)

        # Normalize grid bounds order
        r1, r2 = min(r_min, r_max), max(r_min, r_max)
        c1, c2 = min(c_min, c_max), max(c_min, c_max)

        affected = []
        for r in range(max(0, r1), min(converter.num_rows, r2 + 1)):
            for c in range(max(0, c1), min(converter.num_cols, c2 + 1)):
                affected.append((r, c))

        return affected
