"""
IRIS World Representation Package (Phase 2)
Provides spatial grid discretization, coordinate system conversions,
cell data structures, drivability evaluation logic, and world model facade.
"""

from world.cell import CellState, GridCell
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.grid import OccupancyGrid
from world.world_model import WorldModel

__all__ = [
    "CellState",
    "GridCell",
    "CoordinateConverter",
    "DrivableSpaceEvaluator",
    "OccupancyGrid",
    "WorldModel",
]
