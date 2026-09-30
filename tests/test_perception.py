"""
IRIS Unit & Integration Test Suite — Phase 6: Traffic Perception Layer
Validates perception module, object classes, DetectedObject model, ObjectDetector interface,
SimulatedDetector range and noise models, PerceptionManager validation, coordinate conversion,
evaluation metrics, and end-to-end integration into WorldModel and Risk Engine.
"""

import math
import unittest
import numpy as np

from simulation.environment import SimulationEnvironment
from simulation.entities import TrafficActor, ActorType, BehaviorMode
from perception.object_classes import ObjectClass
from perception.detected_object import DetectedObject
from perception.object_detector import ObjectDetector
from perception.simulated_detector import SimulatedDetector
from perception.perception_manager import PerceptionManager
from perception.coordinate_mapper import CoordinateMapper
from evaluation.perception_metrics import PerceptionEvaluator
from world.world_model import WorldModel
from risk_engine.risk_engine import RiskEngine


class TestPerceptionModule(unittest.TestCase):
    def setUp(self):
        self.env = SimulationEnvironment()
        self.converter = self.env.road  # Reference or default
        self.detector = SimulatedDetector(detection_range=50.0, use_noise=False, seed=42)
        self.manager = PerceptionManager(detector=self.detector)
        self.evaluator = PerceptionEvaluator()

    def test_1_empty_scene(self):
        """Test 1: Empty scene produces no detections."""
        self.env.traffic_actors.clear()
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 0)

    def test_2_single_car(self):
        """Test 2: Single car in scene is correctly detected as CAR class."""
        self.env.traffic_actors = [
            TrafficActor(actor_id=1, actor_type=ActorType.CAR, x=20.0, y=0.0, heading=0.0, velocity=10.0)
        ]
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].object_type, ObjectClass.CAR)
        self.assertTrue(detections[0].object_id.startswith("OBJ_"))
        self.assertGreaterEqual(detections[0].confidence, 0.0)
        self.assertLessEqual(detections[0].confidence, 1.0)

    def test_3_single_pedestrian(self):
        """Test 3: Single pedestrian is correctly detected as PEDESTRIAN class."""
        self.env.traffic_actors = [
            TrafficActor(actor_id=2, actor_type=ActorType.PEDESTRIAN, x=15.0, y=1.0, heading=0.0, velocity=1.2)
        ]
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].object_type, ObjectClass.PEDESTRIAN)

    def test_4_cattle(self):
        """Test 4: Cattle on road is correctly detected as CATTLE class."""
        self.env.traffic_actors = [
            TrafficActor(actor_id=3, actor_type=ActorType.CATTLE, x=25.0, y=-0.5, heading=0.1, velocity=0.5)
        ]
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].object_type, ObjectClass.CATTLE)

    def test_5_mixed_traffic(self):
        """Test 5: Mixed Indian traffic scenario correctly detects all visible classes."""
        self.env.load_scenario("MARKET")
        detections = self.manager.process(self.env)
        self.assertGreater(len(detections), 0)
        
        detected_types = {d.object_type for d in detections}
        self.assertIn(ObjectClass.PEDESTRIAN, detected_types)
        self.assertIn(ObjectClass.MOTORCYCLE, detected_types)
        self.assertIn(ObjectClass.CAR, detected_types)
        self.assertIn(ObjectClass.CATTLE, detected_types)

    def test_6_outside_detection_range(self):
        """Test 6: Object outside 50m sensor range is not detected."""
        self.env.traffic_actors = [
            TrafficActor(actor_id=99, actor_type=ActorType.CAR, x=200.0, y=0.0, heading=0.0, velocity=10.0)
        ]
        # Ego is at x=5.0, actor is at x=200.0 -> distance 195m > 50m
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 0)

    def test_7_invalid_object_rejection(self):
        """Test 7: Malformed detections are safely rejected by PerceptionManager validation."""
        valid_det = DetectedObject(
            object_id="OBJ_001", object_type=ObjectClass.CAR, position=(20.0, 9.0),
            width=1.8, length=4.5, confidence=0.9, source="test", timestamp=0.0
        )
        invalid_det_conf = DetectedObject(
            object_id="OBJ_002", object_type=ObjectClass.CAR, position=(20.0, 9.0),
            width=1.8, length=4.5, confidence=-0.5, source="test", timestamp=0.0
        )
        invalid_det_pos = DetectedObject(
            object_id="OBJ_003", object_type=ObjectClass.CAR, position=(float("nan"), 9.0),
            width=1.8, length=4.5, confidence=0.9, source="test", timestamp=0.0
        )
        invalid_det_dim = DetectedObject(
            object_id="OBJ_004", object_type=ObjectClass.CAR, position=(20.0, 9.0),
            width=-2.0, length=4.5, confidence=0.9, source="test", timestamp=0.0
        )

        self.assertTrue(self.manager.validate_detection(valid_det))
        self.assertFalse(self.manager.validate_detection(invalid_det_conf))
        self.assertFalse(self.manager.validate_detection(invalid_det_pos))
        self.assertFalse(self.manager.validate_detection(invalid_det_dim))
        self.assertFalse(self.manager.validate_detection("not_a_detection_object"))

    def test_8_confidence_validation(self):
        """Test 8: Confidence values stay strictly within [0.0, 1.0]."""
        self.env.load_scenario("J")
        detections = self.manager.process(self.env)
        for det in detections:
            self.assertGreaterEqual(det.confidence, 0.0)
            self.assertLessEqual(det.confidence, 1.0)

    def test_9_position_noise(self):
        """Test 9: Position noise leaves detection near ground truth position."""
        noisy_detector = SimulatedDetector(
            detection_range=50.0, use_noise=True, position_noise_std=0.3, miss_probability=0.0, seed=123
        )
        manager = PerceptionManager(detector=noisy_detector)
        
        self.env.traffic_actors = [
            TrafficActor(actor_id=1, actor_type=ActorType.CAR, x=20.0, y=0.0, heading=0.0, velocity=0.0)
        ]
        detections = manager.process(self.env)
        self.assertEqual(len(detections), 1)
        
        # Ground truth world position: x=20.0, y=0.0+9.0 = 9.0
        det_x, det_y = detections[0].position
        dist = math.hypot(det_x - 20.0, det_y - 9.0)
        self.assertLess(dist, 1.5)  # Error within 1.5m bound for 0.3m std noise

    def test_10_missed_detection(self):
        """Test 10: System handles missed detection without crashing."""
        miss_detector = SimulatedDetector(
            detection_range=50.0, use_noise=True, miss_probability=1.0, seed=42
        )
        manager = PerceptionManager(detector=miss_detector)
        self.env.traffic_actors = [
            TrafficActor(actor_id=1, actor_type=ActorType.CAR, x=20.0, y=0.0, heading=0.0, velocity=5.0)
        ]
        detections = manager.process(self.env)
        self.assertEqual(len(detections), 0)  # Miss probability 1.0 drops object safely

    def test_11_coordinate_conversion(self):
        """Test 11: World coordinate mapping remains accurate across frames."""
        mapper = CoordinateMapper()
        sim_x, sim_y = 30.0, 2.0
        world_x, world_y = mapper.sim_to_world(sim_x, sim_y)
        self.assertEqual(world_x, 30.0)
        self.assertEqual(world_y, 11.0)  # 2.0 + 9.0 lateral offset
        
        grid_r, grid_c = mapper.world_to_grid(world_x, world_y)
        back_x, back_y = mapper.grid_to_world(grid_r, grid_c)
        self.assertAlmostEqual(world_x, back_x, delta=0.5)

    def test_12_evaluation_metrics(self):
        """Test 12: Ground truth vs perception evaluation metrics calculate correctly."""
        self.env.load_scenario("MARKET")
        detections = self.manager.process(self.env)
        
        metrics = self.evaluator.evaluate(
            ground_truth_actors=self.env.traffic_actors,
            detections=detections,
            ego_pos_world=(5.0, 9.0),
            detection_range=50.0
        )

        self.assertIn("precision", metrics)
        self.assertIn("recall", metrics)
        self.assertIn("f1_score", metrics)
        self.assertIn("per_class", metrics)
        self.assertGreaterEqual(metrics["precision"], 0.0)
        self.assertLessEqual(metrics["precision"], 1.0)

    def test_13_end_to_end_integration(self):
        """
        Test 13: End-to-end Integration Test
        Pipeline: Simulation -> SimulatedDetector -> PerceptionManager -> WorldModel -> RiskEngine.
        """
        world_model = WorldModel()
        risk_engine = RiskEngine()

        # 1. Simulation creates traffic actor
        self.env.traffic_actors = [
            TrafficActor(actor_id=101, actor_type=ActorType.CAR, x=25.0, y=0.0, heading=0.0, velocity=8.0)
        ]

        # 2. Detector observes it via PerceptionManager
        detections = self.manager.process(self.env)
        self.assertEqual(len(detections), 1)
        self.assertEqual(detections[0].object_type, ObjectClass.CAR)

        # 3. WorldModel receives perceived objects
        world_model.update_from_environment(self.env, perception_manager=self.manager)
        self.assertEqual(len(world_model.dynamic_actors), 1)
        self.assertEqual(world_model.dynamic_actors[0]["type"], "CAR")

        # 4. Traffic Risk is generated from perceived objects
        risk_grid = risk_engine.update(world_model)
        max_traffic_risk = float(np.max(risk_grid.traffic_risk))
        self.assertGreater(max_traffic_risk, 0.0)


if __name__ == "__main__":
    unittest.main()
