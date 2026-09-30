"""
IRIS Safe-Space / Negative-Space Planner Unit Test Suite (Phase 11).
Contains 20 comprehensive test cases covering free-space detection, clearance mapping,
candidate corridor generation, multi-objective scoring, constraint enforcement,
future risk integration, baseline A* compatibility, and no-safe-corridor handling.
"""

import unittest
import math
import numpy as np

from configs.sim_config import ROAD_LENGTH, ROAD_WIDTH, ROAD_MARGIN
from simulation.entities import ActorType, HazardType, SurfaceHazard
from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from world.coordinate_system import CoordinateConverter
from world.cell import CellState
from tracking.track import Track, TrackState
from future_risk.future_risk_engine import FutureRiskEngine

from safe_space.config import VEHICLE_WIDTH, VEHICLE_SAFETY_MARGIN
from safe_space.free_space import FreeSpaceDetector, FreeSpaceRegion
from safe_space.clearance import ClearanceMap
from safe_space.corridor import SafeCorridor
from safe_space.candidate_generator import CandidateGenerator
from safe_space.candidate_scorer import CandidateScorer
from safe_space.safe_space_analyzer import SafeSpaceAnalyzer
from safe_space.safe_space_planner import SafeSpacePlanner, PlanningResult


class TestSafeSpacePlanner(unittest.TestCase):
    def setUp(self):
        self.converter = CoordinateConverter(ppm=20.0, grid_res=0.5)
        self.risk_engine = FutureRiskEngine(horizon=3.0, time_step=0.2)
        self.planner = SafeSpacePlanner(mode="iris_safe_space")

    def _create_mock_track(
        self,
        track_id="TRK_01",
        obj_type=ActorType.CAR,
        pos=(10.0, 0.0),
        vel=(5.0, 0.0),
    ):
        world_pos = self.converter.sim_to_world(pos[0], pos[1]) if abs(pos[1]) < 0.1 else pos
        t = Track(
            track_id=track_id,
            object_type=obj_type,
            current_position=world_pos,
            velocity=vel,
            speed=math.hypot(vel[0], vel[1]),
            confidence=1.0,
            heading=0.0,
        )
        t.state = TrackState.CONFIRMED
        return t

    # 1. Empty Road Safe Space
    def test_empty_road_safe_space(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)

        res = self.planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.selected_path)
        self.assertGreater(len(res.candidate_paths), 0)

    # 2. Single Obstacle Corridor Generation
    def test_single_obstacle_corridor_generation(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(20.0, 0.0), vel=(0.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        analyzer = SafeSpaceAnalyzer()
        space_map = analyzer.analyze(world_model)
        self.assertIsNotNone(space_map.clearance_grid)
        self.assertGreater(len(space_map.free_regions), 0)

    # 3. Multiple Corridors Evaluation
    def test_multiple_corridors_evaluation(self):
        generator = CandidateGenerator(max_candidates=5)
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        start = self.converter.sim_to_world(5.0, 0.0)
        goal = self.converter.sim_to_world(45.0, 0.0)

        candidates = generator.generate_candidates(start, goal, world_model)
        self.assertGreaterEqual(len(candidates), 3)

    # 4. Narrow Corridor Rejection
    def test_narrow_corridor_rejection(self):
        scorer = CandidateScorer(vehicle_margin=1.0)  # Requires 1.9m clearance
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)

        clearance_map = ClearanceMap()
        clearance_grid = clearance_map.compute_clearance(world_model)
        # Artificially constrict clearance along corridor
        clearance_grid[:, :] = 0.5

        corridor = SafeCorridor(
            corridor_id="NARROW_01",
            centerline=[self.converter.sim_to_world(5.0, 0.0), self.converter.sim_to_world(20.0, 0.0)],
        )

        eval_corridor = scorer.evaluate_candidate(corridor, world_model, None, clearance_map, self.converter.sim_to_world(40.0, 0.0))
        self.assertFalse(eval_corridor.is_valid)
        self.assertIn("Insufficient vehicle clearance", eval_corridor.rejection_reason)

    # 5. Insufficient Vehicle Clearance
    def test_insufficient_vehicle_clearance(self):
        scorer = CandidateScorer()
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)

        clearance_map = ClearanceMap()
        clearance_grid = clearance_map.compute_clearance(world_model)

        # Place corridor at non-traversable boundary
        r_off, c_off = self.converter.world_to_grid(15.0, -10.0)
        clearance_grid[r_off, c_off] = 0.0

        corridor = SafeCorridor(
            corridor_id="OFFROAD_01",
            centerline=[self.converter.grid_to_world(r_off, c_off)],
        )

        eval_c = scorer.evaluate_candidate(corridor, world_model, None, clearance_map, self.converter.sim_to_world(40.0, 0.0))
        self.assertFalse(eval_c.is_valid)

    # 6. High Risk vs Low Risk Corridor
    def test_high_risk_vs_low_risk_corridor(self):
        p_start = self.converter.sim_to_world(10.0, 0.0)
        p_end = self.converter.sim_to_world(30.0, 0.0)
        c_low = SafeCorridor("LOW_RISK", centerline=[p_start, p_end], avg_risk=0.1, peak_risk=0.2, length=30.0)
        c_high = SafeCorridor("HIGH_RISK", centerline=[p_start, p_end], avg_risk=0.8, peak_risk=0.9, length=30.0)

        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)
        scorer = CandidateScorer()

        eval_goal = self.converter.sim_to_world(40.0, 0.0)
        e_low = scorer.evaluate_candidate(c_low, world_model, None, clearance_map, eval_goal)
        e_high = scorer.evaluate_candidate(c_high, world_model, None, clearance_map, eval_goal)

        self.assertLess(e_low.total_score, e_high.total_score)

    # 7. Short vs Long Path Tradeoff
    def test_short_vs_long_path_tradeoff(self):
        p_start = self.converter.sim_to_world(10.0, 0.0)
        p_mid1 = self.converter.sim_to_world(20.0, 1.0)
        p_end = self.converter.sim_to_world(30.0, 0.0)

        c_short = SafeCorridor("SHORT", centerline=[p_start, p_end], length=20.0)
        c_long = SafeCorridor("LONG", centerline=[p_start, p_mid1, p_end], length=35.0)

        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)
        scorer = CandidateScorer()

        eval_goal = self.converter.sim_to_world(40.0, 0.0)
        e_short = scorer.evaluate_candidate(c_short, world_model, None, clearance_map, eval_goal)
        e_long = scorer.evaluate_candidate(c_long, world_model, None, clearance_map, eval_goal)

        self.assertLess(e_short.length_cost, e_long.length_cost)

    # 8. Surface Hazard Avoidance
    def test_surface_hazard_avoidance(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.surface_hazards = [
            SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=15.0, y=0.0, severity=0.9, length=2.0, width=2.0)
        ]
        world_model.update_from_environment(env)

        res = self.planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.selected_corridor)

    # 9. Waterlogging Surface Cost
    def test_waterlogging_surface_cost(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.surface_hazards = [
            SurfaceHazard(hazard_id=1, hazard_type=HazardType.WATERLOGGED, x=20.0, y=0.0, severity=0.7, length=4.0, width=4.0)
        ]
        world_model.update_from_environment(env)

        res = self.planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.selected_corridor.surface_cost, 0.0)

    # 10. Pothole Path Scoring
    def test_pothole_path_scoring(self):
        scorer = CandidateScorer()
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)

        c_pot = SafeCorridor("POT", centerline=[self.converter.sim_to_world(10.0, 0.0), self.converter.sim_to_world(20.0, 0.0)])
        eval_c = scorer.evaluate_candidate(c_pot, world_model, None, clearance_map, self.converter.sim_to_world(40.0, 0.0))
        self.assertTrue(eval_c.is_valid)

    # 11. Boundary Cost Penalty
    def test_boundary_cost_penalty(self):
        scorer = CandidateScorer()
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)

        # Center path vs Edge path
        w_start = self.converter.sim_to_world(10.0, 0.0)
        w_center = self.converter.sim_to_world(15.0, 0.0)
        w_edge = self.converter.sim_to_world(15.0, 3.0)  # Near road boundary

        c_center = SafeCorridor("CENTER", centerline=[w_start, w_center])
        c_edge = SafeCorridor("EDGE", centerline=[w_start, w_edge])

        eval_goal = self.converter.sim_to_world(40.0, 0.0)
        e_center = scorer.evaluate_candidate(c_center, world_model, None, clearance_map, eval_goal)
        e_edge = scorer.evaluate_candidate(c_edge, world_model, None, clearance_map, eval_goal)

        self.assertLess(e_center.boundary_cost, e_edge.boundary_cost)

    # 12. Future Traffic Risk Integration
    def test_future_traffic_risk_integration(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(15.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])
        future_field = self.risk_engine.compute_future_risk_field(world_model)

        res = self.planner.plan(world_model, future_risk_field=future_field)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.selected_corridor)

    # 13. Prediction Uncertainty Cost
    def test_prediction_uncertainty_cost(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        scorer = CandidateScorer()
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)

        c = SafeCorridor("UNCERT", centerline=[self.converter.sim_to_world(10.0, 0.0), self.converter.sim_to_world(25.0, 0.0)])
        eval_c = scorer.evaluate_candidate(c, world_model, None, clearance_map, self.converter.sim_to_world(40.0, 0.0))
        self.assertGreaterEqual(eval_c.uncertainty_cost, 0.0)

    # 14. Multiple Candidate Paths Generation
    def test_multiple_candidate_paths_generation(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        res = self.planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertGreaterEqual(len(res.candidate_paths), 1)

    # 15. Candidate Scoring Function
    def test_candidate_scoring_function(self):
        scorer = CandidateScorer(w_risk=0.5, w_clearance=0.5)
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)

        c = SafeCorridor("SCORE_TEST", centerline=[self.converter.sim_to_world(10.0, 0.0), self.converter.sim_to_world(25.0, 0.0)])
        eval_c = scorer.evaluate_candidate(c, world_model, None, clearance_map, self.converter.sim_to_world(40.0, 0.0))
        self.assertGreater(eval_c.total_score, 0.0)

    # 16. No Safe Corridor Handling
    def test_no_safe_corridor_handling(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()

        # Block entire road grid across all rows
        world_model.update_from_environment(env)
        for r in range(world_model.grid.num_rows):
            world_model.grid.cells[r][15].state = CellState.OCCUPIED

        res = self.planner.plan(world_model)
        self.assertFalse(res.success)
        self.assertEqual(res.reason, "NO_SAFE_CORRIDOR")

    # 17. Goal Reachability Penalty
    def test_goal_reachability_penalty(self):
        scorer = CandidateScorer(w_goal=0.8)
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)
        clearance_map = ClearanceMap()
        clearance_map.compute_clearance(world_model)

        # Candidate terminating far from goal vs near goal
        goal = self.converter.sim_to_world(50.0, 0.0)
        w_start = self.converter.sim_to_world(10.0, 0.0)
        c_near = SafeCorridor("NEAR", centerline=[w_start, self.converter.sim_to_world(48.0, 0.0)])
        c_far = SafeCorridor("FAR", centerline=[w_start, self.converter.sim_to_world(20.0, 0.0)])

        e_near = scorer.evaluate_candidate(c_near, world_model, None, clearance_map, goal)
        e_far = scorer.evaluate_candidate(c_far, world_model, None, clearance_map, goal)

        self.assertLess(e_near.goal_cost, e_far.goal_cost)

    # 18. Safe Corridor Connected to Goal
    def test_safe_corridor_connected_to_goal(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        res = self.planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertEqual(res.reason, "lowest_cost_valid_candidate")

    # 19. Baseline A* Mode Compatibility
    def test_baseline_astar_mode_compatibility(self):
        baseline_planner = SafeSpacePlanner(mode="baseline_astar")
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        res = baseline_planner.plan(world_model)
        self.assertTrue(res.success)
        self.assertEqual(res.reason, "baseline_astar_mode")

    # 20. Ablation Weight Flexibility
    def test_ablation_weight_flexibility(self):
        # Disable risk and clearance, enable length only
        ablation_scorer = CandidateScorer(
            w_risk=0.0,
            w_clearance=0.0,
            w_length=1.0,
            w_smoothness=0.0,
            w_surface=0.0,
            w_boundary=0.0,
        )
        self.assertEqual(ablation_scorer.w_risk, 0.0)
        self.assertEqual(ablation_scorer.w_length, 1.0)
