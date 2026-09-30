"""
IRIS Phase 3 Test Suite: Basic Path Planning & Collision Checking
Tests the 10 core planner requirements:
1. Simple empty-road path finding
2. Start equals goal trivial path
3. Direct static obstacle avoidance
4. Completely blocked road (no-path handling)
5. Pothole avoidance (non-drivable pothole cell)
6. Water avoidance (non-drivable water cell)
7. Road boundary protection
8. Dynamic obstacle current position avoidance
9. Coordinate conversion consistency
10. Path validation & collision checking
"""

import unittest
from world.cell import CellState
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.grid import OccupancyGrid
from world.world_model import WorldModel
from planning.path import Path
from planning.astar import AStarPlanner
from planning.collision_checker import CollisionChecker
from planning.planner import Planner
from simulation.environment import SimulationEnvironment


class TestPlanner(unittest.TestCase):

    def setUp(self):
        self.converter = CoordinateConverter(road_length=100.0, road_width=18.0, grid_res=0.5, ppm=16.0)
        self.evaluator = DrivableSpaceEvaluator()
        self.world_model = WorldModel(converter=self.converter, evaluator=self.evaluator)
        self.planner = Planner(allow_diagonal=False)

    def test_01_empty_road_path(self):
        """1. Verify A* finds a valid path on a clear empty road."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        path = self.planner.plan((10.0, 9.0), (80.0, 9.0), self.world_model)
        self.assertTrue(path.success)
        self.assertTrue(path.valid)
        self.assertGreater(len(path.world_points), 0)
        self.assertGreater(path.length, 0.0)

    def test_02_start_equals_goal(self):
        """2. Verify trivial path generation when start equals goal."""
        self.world_model.grid.reset_grid()
        path = self.planner.plan((25.0, 9.0), (25.0, 9.0), self.world_model)

        self.assertTrue(path.success)
        self.assertTrue(path.valid)
        self.assertEqual(len(path.world_points), 1)
        self.assertEqual(path.length, 0.0)

    def test_03_direct_obstacle_avoidance(self):
        """3. Verify A* detours around a static obstacle placed directly in the path."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        # Place static obstacle directly on straight line (x=40m, y=9m)
        self.world_model.grid.rasterize_oriented_box(
            center_x=40.0, center_y=9.0, length=4.0, width=4.0, heading=0.0,
            state=CellState.OCCUPIED, hazard_type="STATIC_OBSTACLE"
        )

        path = self.planner.plan((10.0, 9.0), (80.0, 9.0), self.world_model)
        self.assertTrue(path.success)
        self.assertTrue(path.valid)

        # Ensure no waypoint in path touches the obstacle cell
        for wx, wy in path.world_points:
            cell = self.world_model.grid.get_cell_at_world(wx, wy)
            self.assertIsNotNone(cell)
            self.assertTrue(cell.is_drivable)

    def test_04_completely_blocked_road(self):
        """4. Verify no-path handling when the road is completely blocked across its full width."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        # Build wall across entire road width at x=40m
        self.world_model.grid.rasterize_oriented_box(
            center_x=40.0, center_y=9.0, length=2.0, width=18.0, heading=0.0,
            state=CellState.OCCUPIED, hazard_type="WALL"
        )

        path = self.planner.plan((10.0, 9.0), (80.0, 9.0), self.world_model)
        self.assertFalse(path.success)
        self.assertFalse(path.valid)
        self.assertEqual(path.status_message, "NO_SAFE_PATH_FOUND")

    def test_05_pothole_avoidance(self):
        """5. Verify A* detours around non-drivable potholes."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        self.world_model.grid.rasterize_circle(
            center_x=30.0, center_y=9.0, radius=2.0, state=CellState.POTHOLE, hazard_type="POTHOLE"
        )

        path = self.planner.plan((10.0, 9.0), (50.0, 9.0), self.world_model)
        self.assertTrue(path.success)
        self.assertTrue(path.valid)

        for wx, wy in path.world_points:
            cell = self.world_model.grid.get_cell_at_world(wx, wy)
            self.assertNotEqual(cell.state, CellState.POTHOLE)

    def test_06_water_avoidance(self):
        """6. Verify A* detours around non-drivable waterlogged sections."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        self.world_model.grid.rasterize_circle(
            center_x=50.0, center_y=9.0, radius=2.5, state=CellState.WATER, hazard_type="WATERLOGGED"
        )

        path = self.planner.plan((20.0, 9.0), (80.0, 9.0), self.world_model)
        self.assertTrue(path.success)
        self.assertTrue(path.valid)

        for wx, wy in path.world_points:
            cell = self.world_model.grid.get_cell_at_world(wx, wy)
            self.assertNotEqual(cell.state, CellState.WATER)

    def test_07_boundary_protection(self):
        """7. Verify planned path never steps outside drivable road width."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        path = self.planner.plan((10.0, 9.0), (80.0, 9.0), self.world_model)
        self.assertTrue(path.success)

        for wx, wy in path.world_points:
            cell = self.world_model.grid.get_cell_at_world(wx, wy)
            self.assertIsNotNone(cell)
            self.assertNotIn(cell.state, (CellState.OUTSIDE_ROAD, CellState.ROAD_BOUNDARY))

    def test_08_dynamic_obstacle_avoidance(self):
        """8. Verify A* avoids the current occupied position of a dynamic actor."""
        env = SimulationEnvironment()
        self.world_model.update_from_environment(env)

        # Get first dynamic actor position transformed to World Grid coordinates
        actor = env.traffic_actors[0]
        actor_wx, actor_wy = self.converter.sim_to_world(actor.x, actor.y)

        path = self.planner.plan((actor_wx - 10.0, actor_wy), (actor_wx + 10.0, actor_wy), self.world_model)
        self.assertTrue(path.success)

        for wx, wy in path.world_points:
            cell = self.world_model.grid.get_cell_at_world(wx, wy)
            self.assertIsNotNone(cell)
            self.assertTrue(cell.is_drivable)


    def test_09_coordinate_conversion_consistency(self):
        """9. Verify Grid and World path point alignment."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        path = self.planner.plan((10.0, 9.0), (30.0, 9.0), self.world_model)
        self.assertTrue(path.success)
        self.assertEqual(len(path.grid_points), len(path.world_points))

        for (r, c), (wx, wy) in zip(path.grid_points, path.world_points):
            r_calc, c_calc = self.converter.world_to_grid(wx, wy)
            self.assertEqual((r, c), (r_calc, c_calc))

    def test_10_path_validation(self):
        """10. Verify CollisionChecker correctly rejects invalid path crossing blocked cells."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        path = self.planner.plan((10.0, 9.0), (50.0, 9.0), self.world_model)
        self.assertTrue(path.valid)

        # Place obstacle on middle waypoint
        mid_x, mid_y = path.world_points[len(path.world_points) // 2]
        self.world_model.grid.rasterize_oriented_box(
            center_x=mid_x, center_y=mid_y, length=2.0, width=2.0, heading=0.0,
            state=CellState.OCCUPIED, hazard_type="NEW_OBSTACLE"
        )

        checker = CollisionChecker()
        is_valid, _ = checker.validate_path(path, self.world_model)
        self.assertFalse(is_valid)


if __name__ == "__main__":
    unittest.main()
