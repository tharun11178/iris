"""
IRIS Multi-Object Tracking Unit and Integration Tests (Phase 7).
Tests all 20 specified tracking unit test cases and end-to-end integration test using standard unittest.
"""

import math
import unittest
from perception.object_classes import ObjectClass
from perception.detected_object import DetectedObject
from tracking.track import Track, TrackState
from tracking.data_association import associate_detections_to_tracks
from tracking.track_manager import TrackManager
from simulation.environment import SimulationEnvironment
from perception.perception_manager import PerceptionManager
from perception.simulated_detector import SimulatedDetector
from world.world_model import WorldModel
from risk_engine.risk_engine import RiskEngine
from evaluation.tracking_metrics import TrackingEvaluator


class TestTrackingModule(unittest.TestCase):
    def setUp(self):
        self.track_mgr = TrackManager(
            match_distance_threshold=3.0,
            min_confirmation_hits=3,
            max_missed_frames=5,
            max_history_length=20,
            velocity_smoothing_alpha=0.6,
        )

    # 1. Empty detection list
    def test_1_empty_detection_list(self):
        tracks = self.track_mgr.update([], timestamp=1.0)
        self.assertEqual(len(tracks), 0)
        self.assertEqual(self.track_mgr.total_tracks_created, 0)

    # 2. One object appearing
    def test_2_one_object_appearing(self):
        det = DetectedObject(
            object_id="DET_001",
            object_type=ObjectClass.CAR,
            position=(10.0, 5.0),
            width=1.8,
            length=4.5,
            confidence=0.9,
            source="sim",
            timestamp=1.0,
        )
        tracks = self.track_mgr.update([det], timestamp=1.0)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].track_id, "TRACK_001")
        self.assertEqual(tracks[0].state, TrackState.TENTATIVE)
        self.assertEqual(tracks[0].hits, 1)

    # 3. Same object across multiple frames
    def test_3_same_object_across_multiple_frames(self):
        for i in range(5):
            t = 1.0 + i * 0.1
            det = DetectedObject(
                object_id=f"DET_{i}",
                object_type=ObjectClass.CAR,
                position=(10.0 + i * 0.5, 5.0),
                width=1.8,
                length=4.5,
                confidence=0.9,
                source="sim",
                timestamp=t,
            )
            tracks = self.track_mgr.update([det], timestamp=t)
            self.assertEqual(len(tracks), 1)
            self.assertEqual(tracks[0].track_id, "TRACK_001")
        self.assertEqual(tracks[0].hits, 5)

    # 4. Multiple objects
    def test_4_multiple_objects(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        det2 = DetectedObject("D2", ObjectClass.PEDESTRIAN, (20.0, 2.0), 0.6, 0.6, 0.85, "sim", 1.0)
        det3 = DetectedObject("D3", ObjectClass.CATTLE, (30.0, -3.0), 1.2, 2.0, 0.88, "sim", 1.0)

        tracks = self.track_mgr.update([det1, det2, det3], timestamp=1.0)
        self.assertEqual(len(tracks), 3)
        track_ids = {t.track_id for t in tracks}
        self.assertEqual(len(track_ids), 3)

    # 5. Different object classes
    def test_5_different_object_classes(self):
        t_car = Track("TRACK_001", ObjectClass.CAR, (10.0, 5.0))
        det_ped = DetectedObject("D1", ObjectClass.PEDESTRIAN, (10.0, 5.0), 0.6, 0.6, 0.9, "sim", 1.0)

        matches, unmatched_tracks, unmatched_dets = associate_detections_to_tracks([t_car], [det_ped])
        self.assertEqual(len(matches), 0)
        self.assertEqual(len(unmatched_tracks), 1)
        self.assertEqual(len(unmatched_dets), 1)

    # 6. Object movement
    def test_6_object_movement(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        self.track_mgr.update([det1], timestamp=1.0)

        det2 = DetectedObject("D2", ObjectClass.CAR, (12.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.1)
        tracks = self.track_mgr.update([det2], timestamp=1.1)

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].current_position, (12.0, 5.0))
        self.assertEqual(tracks[0].previous_position, (10.0, 5.0))

    # 7. Velocity estimation
    def test_7_velocity_estimation(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 0.0), 1.8, 4.5, 0.9, "sim", 1.0)
        self.track_mgr.update([det1], timestamp=1.0)

        # Moves 2 meters in 0.1s => raw vx = 20.0 m/s
        det2 = DetectedObject("D2", ObjectClass.CAR, (12.0, 0.0), 1.8, 4.5, 0.9, "sim", 1.1)
        tracks = self.track_mgr.update([det2], timestamp=1.1)

        self.assertAlmostEqual(tracks[0].velocity[0], 20.0, delta=0.1)
        self.assertAlmostEqual(tracks[0].speed, 20.0, delta=0.1)

    # 8. Velocity smoothing
    def test_8_velocity_smoothing(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (0.0, 0.0), 1.8, 4.5, 0.9, "sim", 0.0)
        self.track_mgr.update([det1], timestamp=0.0)

        # Frame 2: moves 1m in 0.1s => raw v = 10 m/s => smoothed v = 10 m/s
        det2 = DetectedObject("D2", ObjectClass.CAR, (1.0, 0.0), 1.8, 4.5, 0.9, "sim", 0.1)
        self.track_mgr.update([det2], timestamp=0.1)

        # Frame 3: moves 2m in 0.1s => raw v = 20 m/s
        # alpha = 0.6 => v_smooth = 0.6*20 + 0.4*10 = 16.0 m/s
        det3 = DetectedObject("D3", ObjectClass.CAR, (3.0, 0.0), 1.8, 4.5, 0.9, "sim", 0.2)
        tracks = self.track_mgr.update([det3], timestamp=0.2)

        self.assertAlmostEqual(tracks[0].velocity[0], 16.0, delta=0.1)

    # 9. Missed detection
    def test_9_missed_detection(self):
        det = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        self.track_mgr.update([det], timestamp=1.0)
        self.track_mgr.update([det], timestamp=1.1)
        self.track_mgr.update([det], timestamp=1.2)  # Now CONFIRMED (hits=3)

        # Frame 4: object missed
        tracks = self.track_mgr.update([], timestamp=1.3)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].missed_frames, 1)
        self.assertEqual(tracks[0].state, TrackState.LOST)

    # 10. Object reappearing
    def test_10_object_reappearing(self):
        det = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        self.track_mgr.update([det], timestamp=1.0)
        self.track_mgr.update([det], timestamp=1.1)
        self.track_mgr.update([det], timestamp=1.2)  # CONFIRMED

        # Object missed for 2 frames
        self.track_mgr.update([], timestamp=1.3)
        self.track_mgr.update([], timestamp=1.4)

        # Object reappears nearby
        det_reappear = DetectedObject("D1", ObjectClass.CAR, (10.5, 5.0), 1.8, 4.5, 0.9, "sim", 1.5)
        tracks = self.track_mgr.update([det_reappear], timestamp=1.5)

        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0].track_id, "TRACK_001")
        self.assertEqual(tracks[0].state, TrackState.CONFIRMED)
        self.assertEqual(tracks[0].missed_frames, 0)

    # 11. Track confirmation
    def test_11_track_confirmation(self):
        det = DetectedObject("D1", ObjectClass.PEDESTRIAN, (5.0, 2.0), 0.6, 0.6, 0.9, "sim", 1.0)

        t1 = self.track_mgr.update([det], timestamp=1.0)
        self.assertEqual(t1[0].state, TrackState.TENTATIVE)

        t2 = self.track_mgr.update([det], timestamp=1.1)
        self.assertEqual(t2[0].state, TrackState.TENTATIVE)

        t3 = self.track_mgr.update([det], timestamp=1.2)
        self.assertEqual(t3[0].state, TrackState.CONFIRMED)

    # 12. Track deletion
    def test_12_track_deletion(self):
        det = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        self.track_mgr.update([det], timestamp=1.0)

        # Miss object for 6 frames (max_missed_frames = 5)
        for i in range(6):
            tracks = self.track_mgr.update([], timestamp=1.1 + i * 0.1)

        self.assertEqual(len(tracks), 0)
        self.assertEqual(self.track_mgr.total_tracks_deleted, 1)

    # 13. Two nearby objects
    def test_13_two_nearby_objects(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        det2 = DetectedObject("D2", ObjectClass.PEDESTRIAN, (10.5, 5.2), 0.6, 0.6, 0.9, "sim", 1.0)

        tracks = self.track_mgr.update([det1, det2], timestamp=1.0)
        self.assertEqual(len(tracks), 2)
        types = {t.object_type for t in tracks}
        self.assertEqual(types, {ObjectClass.CAR, ObjectClass.PEDESTRIAN})

    # 14. Two same-class objects
    def test_14_two_same_class_objects(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 1.0)
        det2 = DetectedObject("D2", ObjectClass.CAR, (25.0, -2.0), 1.8, 4.5, 0.9, "sim", 1.0)

        tracks = self.track_mgr.update([det1, det2], timestamp=1.0)
        self.assertEqual(len(tracks), 2)
        self.assertNotEqual(tracks[0].track_id, tracks[1].track_id)

    # 15. Crossing objects
    def test_15_crossing_objects(self):
        for i in range(5):
            t = 1.0 + i * 0.1
            det_a = DetectedObject("DA", ObjectClass.CAR, (10.0 + i, 2.0), 1.8, 4.5, 0.9, "sim", t)
            det_b = DetectedObject("DB", ObjectClass.CAR, (20.0 - i, 2.0), 1.8, 4.5, 0.9, "sim", t)

            tracks = self.track_mgr.update([det_a, det_b], timestamp=t)
            self.assertEqual(len(tracks), 2)

    # 16. Track history
    def test_16_track_history(self):
        for i in range(25):
            det = DetectedObject("D1", ObjectClass.CAR, (float(i), 0.0), 1.8, 4.5, 0.9, "sim", float(i))
            tracks = self.track_mgr.update([det], timestamp=float(i))

        # max_history_length = 20
        self.assertEqual(len(tracks[0].history), 20)
        self.assertEqual(tracks[0].history[-1], (24.0, 0.0))

    # 17. Confidence handling
    def test_17_confidence_handling(self):
        det = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.95, "sim", 1.0)
        tracks = self.track_mgr.update([det], timestamp=1.0)
        self.assertEqual(tracks[0].confidence, 0.95)

        # Missed frame -> confidence decays
        tracks = self.track_mgr.update([], timestamp=1.1)
        self.assertLess(tracks[0].confidence, 0.95)
        self.assertGreaterEqual(tracks[0].confidence, 0.1)

    # 18. Invalid detections handling
    def test_18_invalid_detections(self):
        pm = PerceptionManager()
        invalid_det = "not_a_detected_object"
        val = pm.validate_detection(invalid_det)
        self.assertFalse(val)

    # 19. Timestamp handling
    def test_19_timestamp_handling(self):
        det1 = DetectedObject("D1", ObjectClass.CAR, (10.0, 5.0), 1.8, 4.5, 0.9, "sim", 10.5)
        tracks = self.track_mgr.update([det1], timestamp=10.5)
        self.assertEqual(tracks[0].last_timestamp, 10.5)

    # 20. Track ID uniqueness
    def test_20_track_id_uniqueness(self):
        dets = [
            DetectedObject(f"D{i}", ObjectClass.CAR, (float(i * 10), 0.0), 1.8, 4.5, 0.9, "sim", 1.0)
            for i in range(10)
        ]
        tracks = self.track_mgr.update(dets, timestamp=1.0)
        track_ids = [t.track_id for t in tracks]
        self.assertEqual(len(track_ids), len(set(track_ids)))

    # 21. Tracking Metrics Evaluator Test
    def test_21_tracking_evaluator(self):
        evaluator = TrackingEvaluator()
        gt = [{"id": "ACTOR_1", "x": 10.0, "y": 0.0}]
        det = DetectedObject("D1", ObjectClass.CAR, (10.0, 0.0), 1.8, 4.5, 0.9, "sim", 1.0)
        tracks = self.track_mgr.update([det], timestamp=1.0)
        metrics = evaluator.evaluate_frame(gt, tracks, [det])

        self.assertEqual(metrics["active_tracks_count"], 1)
        self.assertEqual(metrics["id_switches"], 0)
        self.assertEqual(metrics["track_continuity"], 1.0)

    # 22. End-to-End Integration Test
    def test_22_phase7_full_integration(self):
        env = SimulationEnvironment()
        pm = PerceptionManager(detector=SimulatedDetector())
        track_mgr = TrackManager()
        wm = WorldModel()
        risk_eng = RiskEngine()

        # Frame 1
        dets1 = pm.process(env)
        tracks1 = track_mgr.update(dets1, timestamp=env.sim_time)
        wm.update_from_environment(env, perception_manager=pm, track_manager=track_mgr)
        risk_eng.update(wm)

        self.assertEqual(len(wm.dynamic_actors), len(tracks1))
        self.assertIsNotNone(risk_eng.risk_grid)

        # Step simulation
        env.step(dt=0.1, throttle=0.5, steering=0.0)

        # Frame 2
        dets2 = pm.process(env)
        tracks2 = track_mgr.update(dets2, timestamp=env.sim_time)
        wm.update_from_environment(env, perception_manager=pm, track_manager=track_mgr)
        risk_eng.update(wm)

        self.assertGreaterEqual(len(tracks2), 1)
        actor_ids = {a["id"] for a in wm.dynamic_actors}
        track_ids = {t.track_id for t in tracks2}
        self.assertEqual(actor_ids, track_ids)


if __name__ == "__main__":
    unittest.main()
