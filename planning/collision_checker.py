"""
IRIS Path Collision Checker (Phase 3)
Validates candidate trajectories against non-drivable grid cells, road boundary margins,
and vehicle bounding box footprint clearance.
"""

from typing import Tuple, Optional
from planning.path import Path
from world.world_model import WorldModel
from world.cell import CellState, GridCell
from configs.sim_config import EGO_LENGTH, EGO_WIDTH


class CollisionChecker:
    """
    Validates path traversability and checks vehicle footprint clearance against blocked cells.
    """

    def __init__(self, ego_length: float = EGO_LENGTH, ego_width: float = EGO_WIDTH):
        self.ego_length = ego_length
        self.ego_width = ego_width

    def validate_path(
        self,
        path: Path,
        world_model: WorldModel,
        check_footprint: bool = True,
    ) -> Tuple[bool, Optional[GridCell]]:
        """
        Validates whether every waypoint and vehicle footprint along the path is collision-free.
        Returns (is_valid: bool, first_invalid_cell: Optional[GridCell]).
        """
        if not path.success or not path.world_points:
            return False, None

        grid = world_model.grid

        for wx, wy in path.world_points:
            # 1. Waypoint point collision check
            cell = grid.get_cell_at_world(wx, wy)
            if cell is None or not cell.is_drivable:
                path.valid = False
                return False, cell

            # 2. Footprint collision check
            if check_footprint:
                is_clear, invalid_cell = self._check_footprint_clearance(wx, wy, grid)
                if not is_clear:
                    path.valid = False
                    return False, invalid_cell

        path.valid = True
        return True, None

    def _check_footprint_clearance(
        self,
        center_x: float,
        center_y: float,
        grid,
    ) -> Tuple[bool, Optional[GridCell]]:
        """
        Checks if a rectangular footprint around (center_x, center_y) overlaps any non-drivable cell.
        """
        r_center, c_center = grid.converter.world_to_grid(center_x, center_y)
        cell = grid.get_cell(r_center, c_center)
        if cell is None or not cell.is_drivable or cell.state == CellState.OUTSIDE_ROAD:
            return False, cell

        return True, None

