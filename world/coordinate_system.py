"""
IRIS Coordinate System Converter (Phase 2)
Provides seamless transformation between:
- World Coordinates (x_meters, y_meters)
- Grid Coordinates (row_index, col_index)
- Screen Coordinates (px, py)
"""

from typing import Tuple, Optional
from configs.sim_config import PPM, GRID_RESOLUTION, ROAD_LENGTH, ROAD_WIDTH, ROAD_MARGIN, SCREEN_WIDTH, SCREEN_HEIGHT


class CoordinateConverter:
    """
    Handles bidirectional conversions across World, Grid, and Screen coordinate spaces.
    
    World Frame:
      - X-axis: Longitudinal road length [0.0, ROAD_LENGTH] (meters)
      - Y-axis: Lateral road position [0.0, ROAD_WIDTH + 2 * ROAD_MARGIN] (meters)
    
    Grid Frame:
      - Rows (Y-axis grid): [0, num_rows - 1]
      - Cols (X-axis grid): [0, num_cols - 1]
    
    Screen Frame:
      - Standard Pygame screen pixel space with camera offset.
    """

    def __init__(
        self,
        road_length: float = ROAD_LENGTH,
        road_width: float = ROAD_WIDTH + 2 * ROAD_MARGIN,
        grid_res: float = GRID_RESOLUTION,
        ppm: float = PPM,
    ):
        self.road_length = road_length
        self.road_width = road_width
        self.grid_res = grid_res
        self.ppm = ppm

        # Compute Grid Dimensions
        self.num_cols = int(round(self.road_length / self.grid_res))
        self.num_rows = int(round(self.road_width / self.grid_res))
        self.lateral_offset = ROAD_MARGIN + (ROAD_WIDTH / 2.0)

    # --- Simulation Frame <-> World Frame Transformations ---

    def sim_to_world(self, sim_x: float, sim_y: float) -> Tuple[float, float]:
        """
        Converts continuous Simulation Environment coordinates (y=0 at road centerline)
        to World Grid coordinates (y=lateral_offset at road centerline).
        """
        return sim_x, sim_y + self.lateral_offset

    def world_to_sim(self, x_world: float, y_world: float) -> Tuple[float, float]:
        """
        Converts World Grid coordinates (y=lateral_offset at road centerline)
        back to continuous Simulation Environment coordinates (y=0 at road centerline).
        """
        return x_world, y_world - self.lateral_offset


    # --- World <-> Grid Transformations ---

    def world_to_grid(self, x_world: float, y_world: float) -> Tuple[int, int]:
        """
        Converts world continuous coordinates (x, y in meters) to grid indices (row, col).
        Clamps to valid grid index range.
        """
        col = int(x_world / self.grid_res)
        row = int(y_world / self.grid_res)

        # Clamp bounds
        col = max(0, min(self.num_cols - 1, col))
        row = max(0, min(self.num_rows - 1, row))

        return row, col

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """
        Converts grid cell indices (row, col) to continuous world coordinates (x, y meters)
        corresponding to the cell center.
        """
        x_world = (col + 0.5) * self.grid_res
        y_world = (row + 0.5) * self.grid_res
        return x_world, y_world

    # --- World <-> Screen Transformations ---

    def world_to_screen(
        self,
        x_world: float,
        y_world: float,
        camera_x: float = 0.0,
        camera_y: float = 0.0,
    ) -> Tuple[int, int]:
        """
        Converts continuous world coordinates (x, y meters) to Pygame screen pixels (px, py).
        Applies camera offset (camera_x, camera_y in meters).
        """
        px = int((x_world - camera_x) * self.ppm)
        py = int((y_world - camera_y) * self.ppm)
        return px, py

    def screen_to_world(
        self,
        px: int,
        py: int,
        camera_x: float = 0.0,
        camera_y: float = 0.0,
    ) -> Tuple[float, float]:
        """
        Converts Pygame screen pixels (px, py) to continuous world coordinates (x, y meters).
        """
        x_world = (px / self.ppm) + camera_x
        y_world = (py / self.ppm) + camera_y
        return x_world, y_world

    # --- Grid <-> Screen Transformations ---

    def grid_to_screen(
        self,
        row: int,
        col: int,
        camera_x: float = 0.0,
        camera_y: float = 0.0,
    ) -> Tuple[int, int]:
        """
        Converts grid cell indices (row, col) directly to top-left Pygame screen pixel coordinates.
        """
        x_world = col * self.grid_res
        y_world = row * self.grid_res
        return self.world_to_screen(x_world, y_world, camera_x, camera_y)
