"""
IRIS Phase 5 Test Suite: Road-Surface Intelligence & SurfaceModel
Tests the 18 core Surface Model requirements:
1. Pothole creation & depth evaluation
2. Water hazard & unknown depth/surface handling
3. Uneven terrain & roughness severity
4. Raised surface & height evaluation
5. Depression hazard & severity evaluation
6. Debris hazard & size/traversability
7. Construction zone hazard creation
8. Severity calculation & normalization
9. Confidence calculation & independence from severity
10. Traversability classification (SAFE, CAUTION, RISKY, NON_TRAVERSABLE)
11. Grid mapping & coordinate conversion
12. Affected cells calculation
13. Influence area calculation
14. Overlapping hazards aggregation (no overwriting)
15. Water with unknown underlying surface risk penalty
16. Minimum dimension / parameter boundary handling
17. Road boundary proximity hazard evaluation
18. Hazard outside road handling
"""

import unittest
import numpy as np

from surface.surface_hazard import SurfaceHazard, SurfaceHazardType, TraversabilityState
from surface.surface_geometry import SurfaceGeometry
from surface.surface_classifier import SurfaceClassifier
from surface.surface_model import SurfaceModel
from world.coordinate_system import CoordinateConverter
from world.drivable_space import DrivableSpaceEvaluator
from world.world_model import WorldModel
from simulation.environment import SimulationEnvironment


class TestSurfaceModel(unittest.TestCase):

    def setUp(self):
        self.converter = CoordinateConverter(road_length=100.0, road_width=18.0, grid_res=0.5, ppm=16.0)
        self.evaluator = DrivableSpaceEvaluator()
        self.world_model = WorldModel(converter=self.converter, evaluator=self.evaluator)
        self.surface_model = self.world_model.surface_model

    def test_01_create_pothole(self):
        """1. Verify pothole hazard creation & depth-severity scaling."""
        pothole = SurfaceHazard("P01", SurfaceHazardType.POTHOLE, (30.0, 9.0), length=2.0, width=1.5, depth=0.12)
        self.surface_model.add_hazard(pothole)

        retrieved = self.surface_model.get_hazard("P01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.hazard_type, SurfaceHazardType.POTHOLE)
        self.assertGreater(retrieved.severity, 0.5)
        self.assertIn(retrieved.traversability, (TraversabilityState.RISKY, TraversabilityState.NON_TRAVERSABLE))

    def test_02_water_hazard_depth(self):
        """2. Verify waterlogged hazard creation & depth evaluation."""
        water = SurfaceHazard("W01", SurfaceHazardType.WATERLOGGING, (45.0, 9.0), length=10.0, width=4.0, depth=0.25)
        self.surface_model.add_hazard(water)

        retrieved = self.surface_model.get_hazard("W01")
        self.assertIsNotNone(retrieved)
        self.assertGreater(retrieved.severity, 0.6)
        self.assertGreater(retrieved.surface_risk, 0.4)

    def test_03_uneven_terrain(self):
        """3. Verify uneven terrain hazard & roughness severity scaling."""
        uneven = SurfaceHazard("U01", SurfaceHazardType.UNEVEN_SURFACE, (60.0, 9.0), length=15.0, width=6.0, roughness=0.7)
        self.surface_model.add_hazard(uneven)

        retrieved = self.surface_model.get_hazard("U01")
        self.assertIsNotNone(retrieved)
        self.assertGreaterEqual(retrieved.severity, 0.5)
        self.assertEqual(retrieved.traversability, TraversabilityState.RISKY)

    def test_04_raised_surface(self):
        """4. Verify speed breaker / raised surface height evaluation."""
        speed_breaker = SurfaceHazard("R01", SurfaceHazardType.RAISED_SURFACE, (40.0, 9.0), length=1.5, width=10.0, height=0.08)
        self.surface_model.add_hazard(speed_breaker)

        retrieved = self.surface_model.get_hazard("R01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.traversability, TraversabilityState.CAUTION)

    def test_05_depression_hazard(self):
        """5. Verify road depression hazard severity & depth evaluation."""
        depression = SurfaceHazard("D01", SurfaceHazardType.DEPRESSION, (50.0, 9.0), length=5.0, width=3.0, depth=0.10)
        self.surface_model.add_hazard(depression)

        retrieved = self.surface_model.get_hazard("D01")
        self.assertIsNotNone(retrieved)
        self.assertGreater(retrieved.severity, 0.3)

    def test_06_debris_hazard(self):
        """6. Verify debris hazard size & traversability classification."""
        debris = SurfaceHazard("DB01", SurfaceHazardType.DEBRIS, (75.0, 9.0), length=2.5, width=2.0)
        self.surface_model.add_hazard(debris)

        retrieved = self.surface_model.get_hazard("DB01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.traversability, TraversabilityState.NON_TRAVERSABLE)

    def test_07_construction_zone(self):
        """7. Verify construction zone hazard creation."""
        czone = SurfaceHazard("CZ01", SurfaceHazardType.CONSTRUCTION, (85.0, 9.0), length=12.0, width=5.0)
        self.surface_model.add_hazard(czone)

        retrieved = self.surface_model.get_hazard("CZ01")
        self.assertIsNotNone(retrieved)
        self.assertGreaterEqual(retrieved.severity, 0.7)

    def test_08_severity_calculation(self):
        """8. Verify severity calculation outputs strictly bounded values in [0.0, 1.0]."""
        sev_shallow = SurfaceClassifier.calculate_severity(SurfaceHazardType.POTHOLE, depth=0.02)
        sev_deep = SurfaceClassifier.calculate_severity(SurfaceHazardType.POTHOLE, depth=0.25)

        self.assertGreater(sev_deep, sev_shallow)
        self.assertLessEqual(sev_deep, 1.0)
        self.assertGreaterEqual(sev_shallow, 0.0)

    def test_09_confidence_independence(self):
        """9. Verify confidence is maintained separately from severity."""
        h1 = SurfaceHazard("H1", SurfaceHazardType.POTHOLE, (30.0, 9.0), length=2.0, width=1.5, severity=0.8, confidence=0.2)
        self.surface_model.add_hazard(h1)

        retrieved = self.surface_model.get_hazard("H1")
        self.assertEqual(retrieved.severity, 0.8)
        self.assertEqual(retrieved.confidence, 0.2)
        self.assertNotEqual(retrieved.severity, retrieved.confidence)

    def test_10_traversability_classification(self):
        """10. Verify correct traversability classification (SAFE, CAUTION, RISKY, NON_TRAVERSABLE)."""
        t_caution = SurfaceClassifier.classify_traversability(SurfaceHazardType.POTHOLE, 0.3, depth=0.04)
        t_risky = SurfaceClassifier.classify_traversability(SurfaceHazardType.POTHOLE, 0.65, depth=0.10)
        t_blocked = SurfaceClassifier.classify_traversability(SurfaceHazardType.POTHOLE, 0.95, depth=0.20)

        self.assertEqual(t_caution, TraversabilityState.CAUTION)
        self.assertEqual(t_risky, TraversabilityState.RISKY)
        self.assertEqual(t_blocked, TraversabilityState.NON_TRAVERSABLE)

    def test_11_grid_mapping(self):
        """11. Verify surface hazard maps accurately to world grid cells."""
        hazard = SurfaceHazard("P02", SurfaceHazardType.POTHOLE, (30.0, 9.0), length=2.0, width=2.0)
        self.surface_model.add_hazard(hazard)

        cells = self.surface_model.get_affected_cells("P02", self.converter)
        self.assertGreater(len(cells), 0)

    def test_12_affected_cells_calculation(self):
        """12. Verify affected cells computation bounds match physical footprint."""
        hazard = SurfaceHazard("P03", SurfaceHazardType.POTHOLE, (50.0, 9.0), length=4.0, width=4.0)
        cells = SurfaceGeometry.get_affected_grid_cells(hazard, self.converter)

        # 4m x 4m footprint at 0.5m grid resolution = ~8x8 = 64 cells
        self.assertGreaterEqual(len(cells), 36)

    def test_13_influence_area_calculation(self):
        """13. Verify hazard influence area expands risk field beyond exact footprint."""
        hazard = SurfaceHazard("P04", SurfaceHazardType.POTHOLE, (50.0, 9.0), length=2.0, width=2.0, severity=0.8, confidence=1.0)
        self.surface_model.add_hazard(hazard)

        # Query point 0.5m outside footprint but within 1.5m influence radius
        risk_near = self.surface_model.get_surface_risk(51.8, 9.0)
        risk_far = self.surface_model.get_surface_risk(60.0, 9.0)

        self.assertGreater(risk_near, 0.0)
        self.assertEqual(risk_far, 0.0)

    def test_14_overlapping_hazards_aggregation(self):
        """14. Verify overlapping hazards aggregate risk probabilistically without overwriting."""
        h1 = SurfaceHazard("H1", SurfaceHazardType.POTHOLE, (40.0, 9.0), length=4.0, width=4.0, severity=0.6, confidence=1.0)
        h2 = SurfaceHazard("H2", SurfaceHazardType.WATERLOGGING, (40.0, 9.0), length=4.0, width=4.0, severity=0.5, confidence=1.0)

        self.surface_model.add_hazard(h1)
        self.surface_model.add_hazard(h2)

        hazards_at = self.surface_model.get_hazards_at(40.0, 9.0)
        self.assertEqual(len(hazards_at), 2)

        combined_risk = self.surface_model.get_surface_risk(40.0, 9.0)
        # Probabilistic combination: 1 - (1 - 0.6) * (1 - 0.5) = 1 - 0.2 = 0.8
        self.assertAlmostEqual(combined_risk, 0.8, delta=0.05)

    def test_15_water_unknown_underlying_surface(self):
        """15. Verify water with unknown underlying surface produces elevated risk penalty."""
        w_known = SurfaceHazard("WK", SurfaceHazardType.WATERLOGGING, (30.0, 9.0), length=4.0, width=4.0, depth=0.10, underlying_surface_known=True)
        w_unknown = SurfaceHazard("WU", SurfaceHazardType.WATERLOGGING, (50.0, 9.0), length=4.0, width=4.0, depth=0.10, underlying_surface_known=False)

        sm1 = SurfaceModel()
        sm1.add_hazard(w_known)
        risk_k = sm1.get_surface_risk(30.0, 9.0)

        sm2 = SurfaceModel()
        sm2.add_hazard(w_unknown)
        risk_u = sm2.get_surface_risk(50.0, 9.0)

        self.assertGreater(risk_u, risk_k)

    def test_16_boundary_dimension_handling(self):
        """16. Verify minimum dimension handling and small bounding box safety."""
        h_tiny = SurfaceHazard("T01", SurfaceHazardType.POTHOLE, (20.0, 9.0), length=0.01, width=0.01)
        self.surface_model.add_hazard(h_tiny)

        retrieved = self.surface_model.get_hazard("T01")
        self.assertGreaterEqual(retrieved.length, 0.1)
        self.assertGreaterEqual(retrieved.width, 0.1)

    def test_17_boundary_proximity_hazard(self):
        """17. Verify boundary proximity hazard detection."""
        h_edge = SurfaceHazard("E01", SurfaceHazardType.DEBRIS, (50.0, 3.2), length=2.0, width=2.0)
        self.surface_model.add_hazard(h_edge)

        hazards = self.surface_model.get_hazards_at(50.0, 3.2)
        self.assertEqual(len(hazards), 1)

    def test_18_hazard_outside_road(self):
        """18. Verify hazard outside road boundary handling."""
        self.world_model.grid.reset_grid()
        self.world_model.grid.mark_road_structure(road_margin=3.0, road_width=12.0, road_length=100.0)

        h_outside = SurfaceHazard("O01", SurfaceHazardType.DEBRIS, (50.0, 0.5), length=2.0, width=2.0)
        self.surface_model.add_hazard(h_outside)

        retrieved = self.surface_model.get_hazard("O01")
        self.assertIsNotNone(retrieved)
        self.assertFalse(self.world_model.is_drivable_at_world(50.0, 0.5))


if __name__ == "__main__":
    unittest.main()
