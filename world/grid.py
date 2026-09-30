"""
IRIS Occupancy Grid (Phase 2)
Implements a 2D spatial grid of GridCell objects representing the environment.
Supports spatial queries, rasterization of bounding boxes/circles, boundary setting,
and drivability map generation.
"""

import math
from typing import List, Tuple, Optional
from world.cell import CellState, GridCell
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator


class OccupancyGrid:
    """
    2D Occupancy & Drivable-Space Grid abstraction.
    """

    def __init__(
        self,
        converter: CoordinateConverter,
        evaluator: Optional[DrivableSpaceEvaluator] = None,
    ):
        self.converter = converter
        self.evaluator = evaluator if evaluator is not None else DrivableSpaceEvaluator()

        self.num_rows = converter.num_rows
        self.num_cols = converter.num_cols
        self.grid_res = converter.grid_res

        # Initialize 2D grid matrix of GridCells
        self.cells: List[List[GridCell]] = []
        self._initialize_grid()

    def _initialize_grid(self):
        """
        Builds matrix of GridCell instances corresponding to spatial centers.
        """
        self.cells = []
        for r in range(self.num_rows):
            row_cells = []
            for c in range(self.num_cols):
                x_world, y_world = self.converter.grid_to_world(r, c)
                cell = GridCell(
                    row=r,
                    col=c,
                    x_world=x_world,
                    y_world=y_world,
                    state=CellState.FREE,
                    is_drivable=True,
                )
                row_cells.append(cell)
            self.cells.append(row_cells)

    def get_cell(self, row: int, col: int) -> Optional[GridCell]:
        """
        Returns GridCell at (row, col) or None if out of bounds.
        """
        if 0 <= row < self.num_rows and 0 <= col < self.num_cols:
            return self.cells[row][col]
        return None

    def get_cell_at_world(self, x_world: float, y_world: float) -> Optional[GridCell]:
        """
        Returns GridCell corresponding to continuous world coordinate (x, y).
        """
        r, c = self.converter.world_to_grid(x_world, y_world)
        return self.get_cell(r, c)

    def reset_grid(self):
        """
        Resets all cells back to FREE state.
        """
        for r in range(self.num_rows):
            for c in range(self.num_cols):
                cell = self.cells[r][c]
                cell.reset(CellState.FREE, True)

    def mark_road_structure(self, road_margin: float, road_width: float, road_length: float):
        """
        Marks road boundaries and off-road shoulder regions across the grid.
        Road Y range: [road_margin, road_margin + road_width]
        """
        y_min_road = road_margin
        y_max_road = road_margin + road_width

        for r in range(self.num_rows):
            for c in range(self.num_cols):
                cell = self.cells[r][c]
                y_center = cell.y_world

                if y_center < y_min_road or y_center > y_max_road:
                    cell.state = CellState.OUTSIDE_ROAD
                elif abs(y_center - y_min_road) < self.grid_res or abs(y_center - y_max_road) < self.grid_res:
                    cell.state = CellState.ROAD_BOUNDARY
                
                self.evaluator.evaluate_cell(cell)

    def rasterize_circle(
        self,
        center_x: float,
        center_y: float,
        radius: float,
        state: CellState,
        hazard_type: str = "NONE",
        severity: float = 0.5,
        confidence: float = 1.0,
        entity_id: Optional[str] = None,
        is_dynamic: bool = False,
    ):
        """
        Rasterizes a circular hazard/object onto the grid cells.
        """
        r_min, c_min = self.converter.world_to_grid(center_x - radius, center_y - radius)
        r_max, c_max = self.converter.world_to_grid(center_x + radius, center_y + radius)

        r2 = radius * radius
        for r in range(r_min, r_max + 1):
            for c in range(c_min, c_max + 1):
                cell = self.get_cell(r, c)
                if cell is None:
                    continue
                dx = cell.x_world - center_x
                dy = cell.y_world - center_y
                if (dx * dx + dy * dy) <= r2:
                    cell.state = state
                    cell.hazard_type = hazard_type
                    cell.occupancy = 1.0
                    cell.severity = severity
                    cell.confidence = confidence
                    cell.entity_id = entity_id
                    cell.is_dynamic = is_dynamic
                    self.evaluator.evaluate_cell(cell)

    def rasterize_oriented_box(
        self,
        center_x: float,
        center_y: float,
        length: float,
        width: float,
        heading: float,
        state: CellState,
        hazard_type: str = "NONE",
        severity: float = 1.0,
        confidence: float = 1.0,
        entity_id: Optional[str] = None,
        is_dynamic: bool = False,
    ):
        """
        Rasterizes an oriented bounding box (OBB) onto the grid cells.
        """
        half_l = length / 2.0
        half_w = width / 2.0
        diag = math.hypot(half_l, half_w)

        r_min, c_min = self.converter.world_to_grid(center_x - diag, center_y - diag)
        r_max, c_max = self.converter.world_to_grid(center_x + diag, center_y + diag)

        cos_h = math.cos(-heading)
        sin_h = math.sin(-heading)

        for r in range(r_min, r_max + 1):
            for c in range(c_min, c_max + 1):
                cell = self.get_cell(r, c)
                if cell is None:
                    continue
                
                # Transform cell position into local box coordinate frame
                dx = cell.x_world - center_x
                dy = cell.y_world - center_y

                local_x = dx * cos_h - dy * sin_h
                local_y = dx * sin_h + dy * cos_h

                if abs(local_x) <= half_l and abs(local_y) <= half_w:
                    cell.state = state
                    cell.hazard_type = hazard_type
                    cell.occupancy = 1.0
                    cell.severity = severity
                    cell.confidence = confidence
                    cell.entity_id = entity_id
                    cell.is_dynamic = is_dynamic
                    self.evaluator.evaluate_cell(cell)
