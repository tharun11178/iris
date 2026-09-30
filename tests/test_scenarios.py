"""
IRIS — Indian Road Intelligence & Safe-space Planner
Combined Phase 14: Scenario Framework & Stress Testing Unit & Integration Tests
"""

import unittest
import random
import numpy as np
from scenarios.scenario_definition import (
    RoadType,
    DifficultyLevel,
    ScenarioDefinition,
    ScenarioMetrics,
)
from scenarios.scenario_loader import ScenarioRegistry
from scenarios.scenario_runner import ScenarioRunner
from scenarios.scenario_manager import ScenarioManager
from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel


class TestScenarioFramework(unittest.TestCase):
    def setUp(self):
        self.registry = ScenarioRegistry()
        self.runner = ScenarioRunner(registry=self.registry)
        self.manager = ScenarioManager(seed=42)
        self.env = SimulationEnvironment()
        self.world_model = WorldModel()

    def test_mandatory_scenarios_exist(self):
        mandatory_ids = [
            "UNMARKED_VILLAGE_ROAD",
            "UNSIGNALIZED_URBAN_INTERSECTION",
            "HIGHWAY_MERGE",
            "DENSE_MARKET",
            "SUDDEN_CATTLE_CROSSING",
        ]
        for sid in mandatory_ids:
            sc = self.registry.get_scenario(sid)
            self.assertIsNotNone(sc, f"Mandatory scenario {sid} missing from registry")
            self.assertEqual(sc.scenario_id, sid)

    def test_surface_scenarios_exist(self):
        surface_ids = [
            "POTHOLE_AVOIDANCE",
            "WATERLOGGING",
            "DEEP_WATER",
            "UNEVEN_TERRAIN",
            "RAISED_SPEED_BREAKER",
            "DEBRIS",
            "CONSTRUCTION",
            "COMBINED_SURFACE_HAZARDS",
        ]
        for sid in surface_ids:
            sc = self.registry.get_scenario(sid)
            self.assertIsNotNone(sc, f"Surface scenario {sid} missing from registry")

    def test_stress_scenarios_exist(self):
        stress_ids = [
            "WRONG_SIDE_MOTORCYCLE",
            "MULTIPLE_CATTLE",
            "PEDESTRIAN_SWARM",
            "SUDDEN_MOTORCYCLE_CUT_IN",
            "BLIND_CURVE",
            "NARROW_ROAD",
            "TWO_OBSTACLE_CORRIDOR",
            "WATER_PLUS_HIDDEN_HAZARD",
            "TRAFFIC_PLUS_POTHOLE",
            "TRAFFIC_PLUS_WATER",
            "MULTI_EVENT_CHAOS",
        ]
        for sid in stress_ids:
            sc = self.registry.get_scenario(sid)
            self.assertIsNotNone(sc, f"Stress scenario {sid} missing from registry")

    def test_seed_reproducibility(self):
        sc1 = self.runner.load_scenario("SUDDEN_CATTLE_CROSSING", seed=42)
        rand1 = [random.random() for _ in range(5)]

        sc2 = self.runner.load_scenario("SUDDEN_CATTLE_CROSSING", seed=42)
        rand2 = [random.random() for _ in range(5)]

        self.assertEqual(rand1, rand2)

    def test_scenario_runner_initialization_and_step(self):
        sc = self.runner.load_scenario("UNMARKED_VILLAGE_ROAD", seed=42)
        self.assertIsNotNone(sc)

        ok = self.runner.initialize_environment(self.env)
        self.assertTrue(ok)
        self.assertGreater(len(self.env.traffic_actors), 0)
        self.assertGreater(len(self.env.surface_hazards), 0)

        # Step simulation environment & scenario runner
        for _ in range(10):
            self.env.sim_time += 0.05
            metrics = self.runner.step(self.env, self.world_model, dt=0.05)

        self.assertEqual(metrics.scenario_id, "UNMARKED_VILLAGE_ROAD")
        self.assertGreater(metrics.total_travel_time, 0.0)

    def test_scenario_matrix_execution(self):
        results = self.manager.run_matrix(seed=42)
        self.assertEqual(len(results), 5)
        for res in results:
            self.assertIn("scenario_id", res)
            self.assertIn("collision_occurred", res)
            self.assertIn("min_clearance_meters", res)


if __name__ == "__main__":
    unittest.main()
