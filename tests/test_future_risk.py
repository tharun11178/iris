"""
Unit and Integration Tests for IRIS Phase 10: Future Risk Field
================================================================
Tests empty road baseline, static surface hazard persistence, moving vehicle/pedestrian/cattle risk movement,
spatial uncertainty expansion, multi-hypothesis conservative aggregation, peak risk calculation,
peak risk time, risk query APIs, non-traversable safety constraints, and end-to-end integration.
"""

import unittest
import math
import numpy as np

from simulation.entities import ActorType, SurfaceHazard, HazardType
from tracking.track import Track, TrackState
from prediction.trajectory import PredictedTrajectory, PredictionHypothesis, PredictionSet
from uncertainty.uncertainty_model import UncertaintySet, UncertaintyState, UncertaintyGrid
from world.world_model import WorldModel
from world.coordinate_system import CoordinateConverter
from simulation.environment import SimulationEnvironment

from future_risk.config import (
    FUTURE_RISK_HORIZON,
    FUTURE_RISK_TIME_STEP,
    HIGH_RISK_THRESHOLD,
)
from future_risk.future_risk_field import FutureRiskField
from future_risk.trajectory_risk import TrajectoryRiskModel
from future_risk.uncertainty_risk import UncertaintyRiskModel
from future_risk.surface_future_risk import SurfaceFutureRiskModel
from future_risk.temporal_risk import TemporalRiskModel
from future_risk.future_risk_engine import FutureRiskEngine


class TestFutureRiskField(unittest.TestCase):
    def setUp(self):
        self.engine = FutureRiskEngine(horizon=3.0, time_step=0.2)
        self.converter = CoordinateConverter(ppm=20.0, grid_res=0.5)

    def _create_mock_track(
        self,
        track_id="TRK_01",
        obj_type=ActorType.CAR,
        pos=(10.0, 0.0),
        vel=(5.0, 0.0),
        heading=0.0,
        confidence=1.0,
    ):
        # Convert simulation y=0.0 to world y=lateral_offset if y is 0.0 or small
        if abs(pos[1]) < 0.1:
            world_pos = self.converter.sim_to_world(pos[0], pos[1])
        else:
            world_pos = pos

        t = Track(
            track_id=track_id,
            object_type=obj_type,
            current_position=world_pos,
            velocity=vel,
            speed=math.hypot(vel[0], vel[1]),
            confidence=confidence,
            heading=heading,
        )
        t.state = TrackState.CONFIRMED
        return t

    # 1. Empty Road Baseline Risk
    def test_empty_road_future_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards.clear()
        world_model.update_from_environment(env)

        field = self.engine.compute_future_risk_field(world_model)
        self.assertEqual(len(field.risk_grids), 16)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(15.0, 0.0))
        self.assertLess(field.get_risk(0, r, c), 0.5)

    # 2. Static Surface Hazard Persistence
    def test_static_surface_hazard_persistence(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.traffic_actors.clear()
        env.surface_hazards = [
            SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=15.0, y=0.0, severity=0.9, length=2.0, width=2.0)
        ]
        world_model.update_from_environment(env)

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(15.0, 0.0))

        # Risk at pothole location must remain high across all future frames (t=0.0s to t=3.0s)
        for i in range(len(field.risk_grids)):
            self.assertGreater(field.get_risk(i, r, c), 0.15)

    # 3. Moving Vehicle Future Risk
    def test_moving_vehicle_future_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)

        # At t=0.0s, peak risk near X=10.0
        r0, c0 = self.converter.world_to_grid(*self.converter.sim_to_world(10.0, 0.0))
        r2, c2 = self.converter.world_to_grid(*self.converter.sim_to_world(20.0, 0.0))

        self.assertGreater(field.get_risk(0, r0, c0), 0.3)
        # At t=1.0s (step 5), vehicle moves to X=20.0 (10 + 10*1.0)
        self.assertGreater(field.get_risk(5, r2, c2), 0.3)

    # 4. Moving Pedestrian Future Risk
    def test_moving_pedestrian_future_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("PED_01", obj_type=ActorType.PEDESTRIAN, pos=(12.0, 1.0), vel=(1.2, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        self.assertEqual(len(field.risk_grids), 16)
        self.assertGreater(field.maximum_risk, 0.2)

    # 5. Moving Motorcycle Future Risk
    def test_moving_motorcycle_future_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("MOTO_01", obj_type=ActorType.MOTORCYCLE, pos=(15.0, -1.0), vel=(8.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        self.assertGreater(field.get_max_risk(0), 0.3)

    # 6. Moving Cattle Future Risk
    def test_moving_cattle_future_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAT_01", obj_type=ActorType.CATTLE, pos=(20.0, 0.5), vel=(0.5, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        self.assertIsNotNone(field.peak_risk_matrix)

    # 7. Multiple Objects Combination
    def test_multiple_objects_combination(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t1 = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(5.0, 0.0))
        t2 = self._create_mock_track("PED_01", obj_type=ActorType.PEDESTRIAN, pos=(25.0, 1.5), vel=(1.0, 0.0))
        world_model.update_from_environment(env, tracks=[t1, t2])

        field = self.engine.compute_future_risk_field(world_model)
        self.assertEqual(len(field.active_tracks), 2)

    # 8. Object Moving Across Grid
    def test_object_moving_across_grid(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(30.0, 0.0))

        # At t=0.0s (step 0), cell X=30 is low risk
        r_t0 = field.get_risk(0, r, c)
        # At t=2.0s (step 10), vehicle arrives at X=30, risk rises
        r_t10 = field.get_risk(10, r, c)
        self.assertGreater(r_t10, r_t0)

    # 9. Risk Movement Over Time
    def test_risk_movement_over_time(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(5.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        self.assertEqual(len(field.timestamps), 16)
        self.assertEqual(field.timestamps[0], 0.0)
        self.assertEqual(field.timestamps[-1], 3.0)

    # 10. Risk Decay After Object Passes
    def test_risk_decay_after_object_passes(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(15.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(10.0, 0.0))

        # Vehicle is at X=10 at t=0.0s (high risk), moves to X=25 at t=1.0s (step 5)
        # Risk at cell X=10 at t=2.0s (step 10) must decay back down
        r_now = field.get_risk(0, r, c)
        r_later = field.get_risk(10, r, c)
        self.assertLess(r_later, r_now)

    # 11. Prediction Uncertainty Expansion
    def test_prediction_uncertainty_expansion(self):
        unc_model = UncertaintyRiskModel(spread_scale=2.0)
        base_r = 2.0
        exp_low = unc_model.calculate_expanded_radius(base_r, uncertainty_score=0.1)
        exp_high = unc_model.calculate_expanded_radius(base_r, uncertainty_score=0.9)
        self.assertGreater(exp_high, exp_low)

    # 12. Multiple Hypotheses Spread
    def test_multiple_hypotheses_spread(self):
        w_start = self.converter.sim_to_world(20.0, 0.0)
        w_t1 = self.converter.sim_to_world(25.0, 0.0)
        w_t2 = self.converter.sim_to_world(25.0, 3.0)

        t1 = PredictedTrajectory("CAT_01", ActorType.CATTLE, w_start, [w_t1], [1.0])
        t2 = PredictedTrajectory("CAT_01", ActorType.CATTLE, w_start, [w_t2], [1.0])
        h1 = PredictionHypothesis("CAT_01", "H1", t1, behavior_type="FORWARD")
        h2 = PredictionHypothesis("CAT_01", "H2", t2, behavior_type="TURN_LEFT")
        pred_set = PredictionSet(timestamp=0.0, trajectories=[t1, t2], hypotheses=[h1, h2], prediction_horizon=3.0)

        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        track = self._create_mock_track("CAT_01", obj_type=ActorType.CATTLE, pos=(20.0, 0.0))
        world_model.update_from_environment(env, tracks=[track], prediction_set=pred_set)

        field = self.engine.compute_future_risk_field(world_model)
        r1, c1 = self.converter.world_to_grid(*w_t1)
        r2, c2 = self.converter.world_to_grid(*w_t2)

        # Risk must exist near both hypothesis branch targets
        self.assertGreater(field.get_risk(5, r1, c1), 0.1)
        self.assertGreater(field.get_risk(5, r2, c2), 0.1)

    # 13. Hypothesis Conservative MAX Aggregation
    def test_hypothesis_conservative_max_aggregation(self):
        traj_model = TrajectoryRiskModel(aggregation_method="MAX")
        self.assertEqual(traj_model.aggregation_method, "MAX")

    # 14. Surface and Traffic Combination
    def test_surface_and_traffic_combination(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        env.surface_hazards = [
            SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=15.0, y=0.0, severity=0.8, length=2.0, width=2.0)
        ]
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(5.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r_pothole, c_pothole = self.converter.world_to_grid(*self.converter.sim_to_world(15.0, 0.0))

        # Both surface hazard and moving traffic contribute to total risk
        self.assertGreater(field.get_risk(0, r_pothole, c_pothole), 0.15)

    # 15. Boundary Risk Persistence
    def test_boundary_risk_persistence(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        field = self.engine.compute_future_risk_field(world_model)
        # Outside road cell (r=0, c=0) must be 1.0 risk across all timesteps
        for i in range(len(field.risk_grids)):
            self.assertEqual(field.get_risk(i, 0, 0), 1.0)

    # 16. Occupied Cell Risk
    def test_occupied_cell_risk(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(10.0, 0.0))
        self.assertGreater(field.get_risk(0, r, c), 0.5)

    # 17. Peak Risk Calculation
    def test_peak_risk_calculation(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(20.0, 0.0))

        peak_r = field.get_peak_risk_over_horizon(r, c)
        self.assertGreater(peak_r, 0.3)

    # 18. Peak Risk Time Calculation
    def test_peak_risk_time_calculation(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(30.0, 0.0))

        peak_t = field.get_time_of_peak_risk(r, c)
        # Vehicle travels 20m from X=10 to X=30 at 10m/s -> arrives at X=30 at t=2.0s
        self.assertAlmostEqual(peak_t, 2.0, delta=0.3)

    # 19. Risk Query API
    def test_risk_query_api(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(5.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        r, c = self.converter.world_to_grid(*self.converter.sim_to_world(10.0, 0.0))

        self.assertGreaterEqual(field.get_risk(0, r, c), 0.0)
        self.assertLessEqual(field.get_risk(0, r, c), 1.0)
        self.assertGreaterEqual(field.get_risk_at_time(0.0, (10.0, 0.0), self.converter), 0.0)
        self.assertGreater(field.get_max_risk(0), 0.0)
        self.assertGreaterEqual(field.get_average_risk(0), 0.0)

        evolution = field.get_risk_evolution(r, c)
        self.assertEqual(len(evolution), 16)
        self.assertEqual(evolution[0][0], 0.0)

    # 20. Horizon Discretization
    def test_horizon_discretization(self):
        temporal = TemporalRiskModel(horizon=3.0, time_step=0.2)
        ts = temporal.generate_timestamps(0.0)
        self.assertEqual(len(ts), 16)
        self.assertEqual(ts[0], 0.0)
        self.assertEqual(ts[-1], 3.0)

    # 21. Risk Normalization
    def test_risk_normalization(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        t = self._create_mock_track("CAR_01", pos=(10.0, 0.0), vel=(10.0, 0.0))
        world_model.update_from_environment(env, tracks=[t])

        field = self.engine.compute_future_risk_field(world_model)
        for grid in field.risk_grids:
            self.assertTrue(np.all(grid.total_risk >= 0.0))
            self.assertTrue(np.all(grid.total_risk <= 1.0))

    # 22. Non-Traversable Cells Protected
    def test_non_traversable_cells_protected(self):
        world_model = WorldModel(converter=self.converter)
        env = SimulationEnvironment()
        world_model.update_from_environment(env)

        field = self.engine.compute_future_risk_field(world_model)
        # Out-of-bounds / road edge cell (r=0, c=0) remains 1.0 risk
        for grid in field.risk_grids:
            self.assertEqual(grid.total_risk[0, 0], 1.0)


if __name__ == "__main__":
    unittest.main()
