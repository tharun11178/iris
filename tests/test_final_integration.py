"""
IRIS Final Integration & System Robustness Test Suite (Combined Phase 16).
Tests MATLAB/Simulink/RoadRunner Adapters, Multi-Sensor Pipeline, Demo Runner,
and System Safety / Edge-Case Robustness.
"""

import os
import shutil
import unittest
import numpy as np

from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from perception.sensor_pipeline import SensorPipeline, CameraFrame, LiDARPointCloud, RadarScan
from integration.matlab.matlab_adapter import MatlabAdapter
from integration.simulink.simulink_adapter import SimulinkAdapter
from integration.roadrunner.roadrunner_actor_mapping import RoadRunnerActorMapper
from integration.roadrunner.roadrunner_scene_spec import RoadRunnerSceneSpecGenerator
from demo.demo_runner import DemoRunner


class TestFinalIntegrationAndRobustness(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_final_output"
        os.makedirs(self.test_dir, exist_ok=True)
        self.env = SimulationEnvironment()
        self.world_model = WorldModel()

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_matlab_adapter_serialization(self):
        adapter = MatlabAdapter(exchange_file=os.path.join(self.test_dir, "test_matlab_ipc.json"))
        payload = adapter.serialize_iris_state(self.env)

        self.assertIn("ego_vehicle", payload)
        self.assertIn("traffic_actors", payload)
        self.assertIn("metrics", payload)

        filepath = adapter.export_to_file(payload)
        self.assertTrue(os.path.exists(filepath))

        read_payload = adapter.import_from_file(filepath)
        self.assertIsNotNone(read_payload)
        self.assertEqual(read_payload["ego_vehicle"]["speed_kmh"], payload["ego_vehicle"]["speed_kmh"])

        parsed_ctrl = adapter.parse_matlab_control_response({
            "steering_angle_deg": 5.0,
            "target_speed_kmh": 25.0,
            "throttle": 0.5,
            "brake": 0.0
        })
        self.assertAlmostEqual(parsed_ctrl["target_speed_ms"], 25.0 / 3.6, places=2)

    def test_simulink_adapter_bus_signals(self):
        adapter = SimulinkAdapter()
        bus_payload = adapter.export_simulink_bus_signals(self.env)

        self.assertIn("EgoVehicleBus", bus_payload)
        self.assertIn("TargetTrajectoryBus", bus_payload)
        self.assertIn("DecisionSafetyBus", bus_payload)
        self.assertIn("ControlCommandBus", bus_payload)

        filepath = os.path.join(self.test_dir, "test_bus.json")
        out_path = adapter.save_bus_data(bus_payload, filepath)
        self.assertTrue(os.path.exists(out_path))

    def test_roadrunner_asset_mapping_and_scenes(self):
        act_car = RoadRunnerActorMapper.map_roadrunner_asset("Vehicle.Car.Hatchback")
        self.assertEqual(act_car.name, "CAR")

        act_rickshaw = RoadRunnerActorMapper.map_roadrunner_asset("Vehicle.Rickshaw.Auto")
        self.assertEqual(act_rickshaw.name, "AUTO_RICKSHAW")

        act_cattle = RoadRunnerActorMapper.map_roadrunner_asset("Animal.Cattle.Cow")
        self.assertEqual(act_cattle.name, "CATTLE")

        hz_pothole = RoadRunnerActorMapper.map_roadrunner_hazard("Hazard.Surface.Pothole")
        self.assertEqual(hz_pothole.name, "POTHOLE")

        s1 = RoadRunnerSceneSpecGenerator.generate_scene_1_urban_intersection()
        self.assertEqual(s1["scene_id"], "ROADRUNNER_SCENE_1_URBAN_INTERSECTION")

        s2 = RoadRunnerSceneSpecGenerator.generate_scene_2_village_highway_transition()
        self.assertEqual(s2["scene_id"], "ROADRUNNER_SCENE_2_VILLAGE_HIGHWAY_TRANSITION")

        exported = RoadRunnerSceneSpecGenerator.export_all_scenes(self.test_dir)
        self.assertTrue(os.path.exists(exported["scene_1"]))
        self.assertTrue(os.path.exists(exported["scene_2"]))

    def test_sensor_pipeline_streams(self):
        pipeline = SensorPipeline()
        streams = pipeline.process_sensor_streams(self.env)

        self.assertIn("camera", streams)
        self.assertIn("lidar", streams)
        self.assertIn("radar", streams)
        self.assertIsInstance(streams["camera"], CameraFrame)
        self.assertIsInstance(streams["lidar"], LiDARPointCloud)
        self.assertIsInstance(streams["radar"], RadarScan)

    def test_demo_runner_execution(self):
        demo = DemoRunner(seed=42, headless=True)
        res = demo.run_demo_sequence(duration_scale=0.1)
        self.assertIn("scenarios_evaluated", res)
        self.assertGreater(res["scenarios_evaluated"], 0)


if __name__ == "__main__":
    unittest.main()
