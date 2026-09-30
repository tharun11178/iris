"""
IRIS High-Level Planner Facade (Phase 3)
Abstracts path search algorithm and path validation from simulation/visualization logic.
Provides unified plan() and replan_if_blocked() execution methods.
"""

from typing import Tuple, Optional
from planning.path import Path
from planning.astar import AStarPlanner
from planning.collision_checker import CollisionChecker
from world.world_model import WorldModel


class Planner:
    """
    High-level Planner interface.
    """

    def __init__(self, allow_diagonal: bool = False):
        self.astar = AStarPlanner(allow_diagonal=allow_diagonal)
        self.checker = CollisionChecker()
        self.active_path: Optional[Path] = None

    def plan(
        self,
        start_world: Tuple[float, float],
        goal_world: Tuple[float, float],
        world_model: WorldModel,
    ) -> Path:
        """
        Generates and validates a collision-free path from start to goal.
        """
        path = self.astar.plan(start_world, goal_world, world_model)

        if path.success:
            is_valid, _ = self.checker.validate_path(path, world_model)
            path.valid = is_valid

        self.active_path = path
        return path

    def validate_current_path(self, world_model: WorldModel) -> bool:
        """
        Checks if the active path remains collision-free under current world state.
        """
        if self.active_path is None or not self.active_path.success:
            return False

        is_valid, _ = self.checker.validate_path(self.active_path, world_model)
        return is_valid
