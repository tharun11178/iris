"""
IRIS Perception Coordinate Mapper (Phase 6).
Provides coordinate transformation interfaces for sensor, world, grid, and screen frames,
reusing Phase 2 CoordinateConverter functionality.
"""

from typing import Tuple, Optional
from world.coordinate_system import CoordinateConverter


class CoordinateMapper:
    """
    Handles coordinate space transformations for perception module.
    Delegates to central Phase 2 CoordinateConverter to prevent code duplication.
    """

    def __init__(self, converter: Optional[CoordinateConverter] = None):
        self.converter = converter if converter is not None else CoordinateConverter()

    def sensor_to_world(self, sensor_x: float, sensor_y: float, sensor_origin_world: Tuple[float, float] = (0.0, 0.0), sensor_yaw: float = 0.0) -> Tuple[float, float]:
        """
        Transforms relative sensor coordinates (ego-centric) to continuous World coordinates.
        :param sensor_x: Longitudinal relative position in meters.
        :param sensor_y: Lateral relative position in meters.
        :param sensor_origin_world: Sensor/Ego origin (x, y) in world frame.
        :param sensor_yaw: Sensor/Ego orientation in radians.
        """
        ox, oy = sensor_origin_world
        import math
        cos_y = math.cos(sensor_yaw)
        sin_y = math.sin(sensor_yaw)

        # Rotate relative sensor vector by yaw and translate by origin
        world_x = ox + (sensor_x * cos_y - sensor_y * sin_y)
        world_y = oy + (sensor_x * sin_y + sensor_y * cos_y)
        return world_x, world_y

    def sim_to_world(self, sim_x: float, sim_y: float) -> Tuple[float, float]:
        """Converts continuous simulation coordinates (y=0 at centerline) to World coordinates."""
        return self.converter.sim_to_world(sim_x, sim_y)

    def world_to_sim(self, x_world: float, y_world: float) -> Tuple[float, float]:
        """Converts World coordinates back to simulation coordinates."""
        return self.converter.world_to_sim(x_world, y_world)

    def world_to_grid(self, x_world: float, y_world: float) -> Tuple[int, int]:
        """Converts continuous World coordinates (x, y meters) to grid indices (row, col)."""
        return self.converter.world_to_grid(x_world, y_world)

    def grid_to_world(self, row: int, col: int) -> Tuple[float, float]:
        """Converts grid cell indices (row, col) to continuous World coordinates (x, y meters)."""
        return self.converter.grid_to_world(row, col)

    def world_to_screen(self, x_world: float, y_world: float, camera_x: float = 0.0, camera_y: float = 0.0) -> Tuple[int, int]:
        """Converts World coordinates (x, y meters) to screen pixel coordinates (px, py)."""
        return self.converter.world_to_screen(x_world, y_world, camera_x, camera_y)
