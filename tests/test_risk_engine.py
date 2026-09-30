"""
IRIS Phase 4 Test Suite: IRIS Spatial Risk Engine & Risk Map
Tests the 12 core Risk Engine requirements:
1. Empty road baseline risk evaluation
2. Dynamic vehicle traffic risk field & spatial decay
3. Pedestrian traffic risk evaluation
4. Cattle traffic risk evaluation
5. Pothole surface risk evaluation
6. Waterlogged road surface risk evaluation
7. Uneven road surface risk evaluation
8. Road boundary risk evaluation
9. Multiple overlapping risk factors accumulation
10. Occupied cell max risk enforcement
11. Total risk grid normalization check [0.0, 1.0]
12. Zero-hazard baseline risk check
"""

import unittest
import numpy as np

from world.cell import CellState
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.world_model import WorldModel
from risk_engine.risk_engine import RiskEngine
from risk_engine.risk_grid import RiskGrid
from simulation.environment import SimulationEnvironment
from simulation.entities import ActorType, HazardType, TrafficActor, SurfaceHazard


class TestRiskEngine(unittest.TestCase):

    def setUp(self):
        self.converter = CoordinateConverter(road_length=100.0, road_width=18.0, grid_res=0.5, ppm=16.0)
        self.evaluator = DrivableSpaceEvaluator()
        self.world_model = WorldModel(converter=self.converter, evaluator=self.evaluator)
        self.risk_engine = RiskEngine()

    def test_01_empty_road_risk(self):
        """1. Verify low risk on a clear, empty road centerline."""
        env = SimulationEnvironment()
        env.traffic_actors = []
        env.surface_hazards = []
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        r, c = self.converter.world_to_grid(50.0, 9.0)  # Road centerline (y=9.0 in world coords)

        # Centerline on empty road should have near-zero traffic, surface, and collision risk
        self.assertLess(risk_grid.traffic_risk[r, c], 0.01)
        self.assertLess(risk_grid.surface_risk[r, c], 0.01)
        self.assertLess(risk_grid.collision_risk[r, c], 0.01)
        self.assertLess(risk_grid.total_risk[r, c], 0.20)  # Total low

    def test_02_vehicle_traffic_risk(self):
        """2. Verify traffic risk rises near a vehicle and decays with distance."""
        env = SimulationEnvironment()
        env.traffic_actors = [
            TrafficActor(1, ActorType.CAR, 50.0, 0.0, heading=0.0, velocity=10.0)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)

        r_near, c_near = self.converter.world_to_grid(52.0, 9.0)   # 2m away
        r_far, c_far = self.converter.world_to_grid(65.0, 9.0)     # 15m away

        self.assertGreater(risk_grid.traffic_risk[r_near, c_near], 0.30)
        self.assertGreater(risk_grid.traffic_risk[r_near, c_near], risk_grid.traffic_risk[r_far, c_far])

    def test_03_pedestrian_traffic_risk(self):
        """3. Verify high localized traffic risk produced by a pedestrian actor."""
        env = SimulationEnvironment()
        env.traffic_actors = [
            TrafficActor(1, ActorType.PEDESTRIAN, 40.0, 2.0, heading=1.57, velocity=1.2)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        ped_wx, ped_wy = self.converter.sim_to_world(40.0, 2.0)
        r, c = self.converter.world_to_grid(ped_wx, ped_wy)

        self.assertGreater(risk_grid.traffic_risk[r, c], 0.50)

    def test_04_cattle_traffic_risk(self):
        """4. Verify traffic risk produced by cattle with higher weight and influence."""
        env = SimulationEnvironment()
        env.traffic_actors = [
            TrafficActor(1, ActorType.CATTLE, 45.0, -1.0, heading=0.0, velocity=0.5)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        cattle_wx, cattle_wy = self.converter.sim_to_world(45.0, -1.0)
        r, c = self.converter.world_to_grid(cattle_wx, cattle_wy)

        self.assertGreater(risk_grid.traffic_risk[r, c], 0.60)

    def test_05_pothole_surface_risk(self):
        """5. Verify surface risk field around a pothole hazard."""
        env = SimulationEnvironment()
        env.surface_hazards = [
            SurfaceHazard(1, HazardType.POTHOLE, 30.0, 0.0, length=2.0, width=2.0, severity=0.8)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        pot_wx, pot_wy = self.converter.sim_to_world(30.0, 0.0)
        r, c = self.converter.world_to_grid(pot_wx, pot_wy)

        self.assertGreater(risk_grid.surface_risk[r, c], 0.50)

    def test_06_waterlogged_surface_risk(self):
        """6. Verify surface risk field for waterlogged patch with severity & uncertainty."""
        env = SimulationEnvironment()
        env.surface_hazards = [
            SurfaceHazard(1, HazardType.WATERLOGGED, 60.0, 0.0, length=4.0, width=4.0, severity=0.9, uncertainty=0.1)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        w_wx, w_wy = self.converter.sim_to_world(60.0, 0.0)
        r, c = self.converter.world_to_grid(w_wx, w_wy)

        self.assertGreater(risk_grid.surface_risk[r, c], 0.50)

    def test_07_uneven_road_surface_risk(self):
        """7. Verify surface risk field around uneven terrain."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        self.world_model.grid.rasterize_circle(
            center_x=70.0, center_y=9.0, radius=2.0, state=CellState.UNEVEN_TERRAIN, hazard_type="UNEVEN", severity=0.8
        )

        risk_grid = self.risk_engine.update(self.world_model)
        r, c = self.converter.world_to_grid(70.0, 9.0)

        self.assertGreaterEqual(risk_grid.surface_risk[r, c], 0.30)

    def test_08_road_boundary_risk(self):
        """8. Verify boundary risk increases near road edges and outside road margins."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        risk_grid = self.risk_engine.update(self.world_model)

        r_center, c_center = self.converter.world_to_grid(50.0, 9.0)  # Centerline
        r_edge, c_edge = self.converter.world_to_grid(50.0, 3.2)      # Near road edge (y=3.0 is boundary)
        r_outside, c_outside = self.converter.world_to_grid(50.0, 1.0) # Outside road

        self.assertGreater(risk_grid.boundary_risk[r_edge, c_edge], risk_grid.boundary_risk[r_center, c_center])
        self.assertEqual(risk_grid.boundary_risk[r_outside, c_outside], 1.0)

    def test_09_multiple_risk_factors_accumulation(self):
        """9. Verify multi-object traffic risk combination preserves smooth accumulation <= 1.0."""
        env = SimulationEnvironment()
        env.traffic_actors = [
            TrafficActor(1, ActorType.CAR, 50.0, 0.0, heading=0.0, velocity=5.0),
            TrafficActor(2, ActorType.AUTO_RICKSHAW, 53.0, 1.0, heading=0.0, velocity=4.0),
            TrafficActor(3, ActorType.PEDESTRIAN, 51.0, -1.0, heading=0.0, velocity=1.0)
        ]
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)
        wx, wy = self.converter.sim_to_world(52.0, 0.0)
        r, c = self.converter.world_to_grid(wx, wy)

        self.assertGreater(risk_grid.traffic_risk[r, c], 0.70)
        self.assertLessEqual(risk_grid.traffic_risk[r, c], 1.0)

    def test_10_occupied_cell_max_risk(self):
        """10. Verify occupied cells receive collision risk 1.0 and total risk >= 0.95."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        # Mark an occupied block
        self.world_model.grid.rasterize_oriented_box(
            center_x=40.0, center_y=9.0, length=4.0, width=4.0, heading=0.0,
            state=CellState.OCCUPIED, hazard_type="OBSTACLE"
        )

        risk_grid = self.risk_engine.update(self.world_model)
        r, c = self.converter.world_to_grid(40.0, 9.0)

        self.assertEqual(risk_grid.collision_risk[r, c], 1.0)
        self.assertGreaterEqual(risk_grid.total_risk[r, c], 0.95)

    def test_11_risk_normalization(self):
        """11. Verify all total risk grid values across entire grid are strictly within [0.0, 1.0]."""
        env = SimulationEnvironment()
        self.world_model.update_from_environment(env)
        risk_grid = self.risk_engine.update(self.world_model)

        self.assertTrue(np.all(risk_grid.total_risk >= 0.0))
        self.assertTrue(np.all(risk_grid.total_risk <= 1.0))
        self.assertTrue(np.all(risk_grid.traffic_risk >= 0.0))
        self.assertTrue(np.all(risk_grid.traffic_risk <= 1.0))
        self.assertTrue(np.all(risk_grid.surface_risk >= 0.0))
        self.assertTrue(np.all(risk_grid.surface_risk <= 1.0))

    def test_12_zero_hazard_baseline(self):
        """12. Verify zero-hazard baseline risk stay low when no hazards/actors exist."""
        env = SimulationEnvironment()
        env.traffic_actors = []
        env.surface_hazards = []
        self.world_model.update_from_environment(env)

        risk_grid = self.risk_engine.update(self.world_model)

        self.assertEqual(np.max(risk_grid.traffic_risk), 0.0)
        self.assertEqual(np.max(risk_grid.surface_risk), 0.0)
        self.assertGreater(risk_grid.get_max_risk(), 0.0)  # Boundary risk exists at edges
        self.assertLess(risk_grid.get_average_risk(), 0.30)


if __name__ == "__main__":
    unittest.main()
