"""
IRIS Phase 2 Test Suite: World Representation & Drivable-Space Model
Tests the 10 core requirements:
1. Grid creation & dimensions
2. Coordinate conversion consistency
3. Road boundary detection & rasterization
4. Obstacle insertion
5. Pothole hazard rasterization
6. Water hazard rasterization
7. Drivable-cell detection logic
8. Dynamic-object registration
9. Vehicle position registration
10. Goal position registration & spatial query
"""

import unittest
from world.cell import CellState, GridCell
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.grid import OccupancyGrid
from world.world_model import WorldModel
from simulation.environment import SimulationEnvironment


class TestWorldModel(unittest.TestCase):

    def setUp(self):
        self.converter = CoordinateConverter(road_length=100.0, road_width=18.0, grid_res=0.5, ppm=16.0)
        self.evaluator = DrivableSpaceEvaluator()
        self.world_model = WorldModel(converter=self.converter, evaluator=self.evaluator)

    def test_01_grid_creation(self):
        """1. Verify grid creation and correct cell matrix dimensions."""
        grid = self.world_model.grid
        self.assertEqual(grid.num_cols, int(100.0 / 0.5))
        self.assertEqual(grid.num_rows, int(18.0 / 0.5))
        self.assertIsNotNone(grid.get_cell(0, 0))

    def test_02_coordinate_conversion(self):
        """2. Verify bidirectional transformation between World and Grid coordinates."""
        x_world, y_world = 25.4, 9.2
        r, c = self.converter.world_to_grid(x_world, y_world)
        wx_recon, wy_recon = self.converter.grid_to_world(r, c)

        self.assertAlmostEqual(x_world, wx_recon, delta=0.5)
        self.assertAlmostEqual(y_world, wy_recon, delta=0.5)

    def test_03_road_boundary_detection(self):
        """3. Verify road boundaries and outside-road shoulder identification."""
        grid = self.world_model.grid
        grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        # Outside road shoulder check (y = 1.0m < margin=3.0m)
        cell_outside = grid.get_cell_at_world(50.0, 1.0)
        self.assertIsNotNone(cell_outside)
        self.assertEqual(cell_outside.state, CellState.OUTSIDE_ROAD)
        self.assertFalse(cell_outside.is_drivable)

        # Center road check (y = 9.0m, inside [3.0, 15.0])
        cell_inside = grid.get_cell_at_world(50.0, 9.0)
        self.assertIsNotNone(cell_inside)
        self.assertEqual(cell_inside.state, CellState.FREE)
        self.assertTrue(cell_inside.is_drivable)

    def test_04_obstacle_insertion(self):
        """4. Verify static obstacle rasterization onto grid."""
        grid = self.world_model.grid
        grid.rasterize_oriented_box(
            center_x=40.0, center_y=9.0, length=4.0, width=2.0, heading=0.0,
            state=CellState.OCCUPIED, hazard_type="STATIC_OBSTACLE"
        )
        cell = grid.get_cell_at_world(40.0, 9.0)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.state, CellState.OCCUPIED)
        self.assertFalse(cell.is_drivable)

    def test_05_pothole_insertion(self):
        """5. Verify pothole circular hazard rasterization."""
        grid = self.world_model.grid
        grid.rasterize_circle(
            center_x=30.0, center_y=9.0, radius=1.0, state=CellState.POTHOLE, hazard_type="POTHOLE"
        )
        cell = grid.get_cell_at_world(30.0, 9.0)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.state, CellState.POTHOLE)
        self.assertFalse(cell.is_drivable)

    def test_06_water_insertion(self):
        """6. Verify waterlogged region rasterization."""
        grid = self.world_model.grid
        grid.rasterize_circle(
            center_x=60.0, center_y=9.0, radius=2.0, state=CellState.WATER, hazard_type="WATERLOGGED"
        )
        cell = grid.get_cell_at_world(60.0, 9.0)
        self.assertIsNotNone(cell)
        self.assertEqual(cell.state, CellState.WATER)
        self.assertFalse(cell.is_drivable)

    def test_07_drivable_cell_detection(self):
        """7. Verify drivable space evaluator rules."""
        cell = GridCell(row=0, col=0, x_world=0.0, y_world=0.0, state=CellState.FREE)
        self.assertTrue(self.evaluator.evaluate_cell(cell))

        cell.state = CellState.OCCUPIED
        self.assertFalse(self.evaluator.evaluate_cell(cell))

    def test_08_dynamic_object_registration(self):
        """8. Verify dynamic traffic actor registration in WorldModel."""
        env = SimulationEnvironment()
        self.world_model.update_from_environment(env)
        self.assertGreater(len(self.world_model.dynamic_actors), 0)

    def test_09_vehicle_position_registration(self):
        """9. Verify Ego vehicle position and state registration."""
        env = SimulationEnvironment()
        self.world_model.update_from_environment(env)
        self.assertIn("x", self.world_model.ego_state)
        self.assertIn("speed", self.world_model.ego_state)

    def test_10_goal_registration(self):
        """10. Verify destination goal setting and spatial query."""
        self.world_model.set_goal_position(90.0, 9.0)
        self.assertEqual(self.world_model.goal_position, (90.0, 9.0))


if __name__ == "__main__":
    unittest.main()
