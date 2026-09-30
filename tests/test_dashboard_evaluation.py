"""
IRIS Unit & Integration Test Suite for Combined Phase 15.
Tests Metrics Engine, Ablation Configurations, Benchmark Comparator, Report Generator, and Experiment Runner.
"""

import os
import shutil
import unittest
import numpy as np

from evaluation.metrics import MetricsCalculator, CollisionRecord, SmoothnessMetrics
from evaluation.scenario_metrics import ExtendedScenarioMetrics, ScenarioMetricsTracker
from evaluation.ablation_config import AblationConfig
from evaluation.comparison import BenchmarkComparator
from evaluation.report import ReportGenerator
from experiment_runner import ExperimentRunner


class TestPhase15EvaluationAndDashboard(unittest.TestCase):

    def setUp(self):
        self.test_out_dir = "test_experiment_results"
        os.makedirs(self.test_out_dir, exist_ok=True)
        self.calculator = MetricsCalculator(near_collision_threshold=1.2)

    def tearDown(self):
        if os.path.exists(self.test_out_dir):
            shutil.rmtree(self.test_out_dir, ignore_errors=True)

    def test_metrics_calculator_ttc(self):
        # Approaching head-on at relative speed 10 m/s from 20m away
        ttc = self.calculator.calculate_ttc(
            ego_x=0.0, ego_y=0.0, ego_vx=10.0, ego_vy=0.0,
            actor_x=20.0, actor_y=0.0, actor_vx=0.0, actor_vy=0.0,
            ego_radius=2.0, actor_radius=1.5
        )
        self.assertAlmostEqual(ttc, (20.0 - 3.5) / 10.0, places=2)

    def test_metrics_calculator_smoothness(self):
        straight_path = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
        sm_straight = self.calculator.calculate_path_smoothness(straight_path)
        self.assertGreaterEqual(sm_straight.smoothness_score, 0.95)

        zigzag_path = [(0.0, 0.0), (1.0, 2.0), (2.0, -2.0), (3.0, 2.0)]
        sm_zigzag = self.calculator.calculate_path_smoothness(zigzag_path)
        self.assertLess(sm_zigzag.smoothness_score, sm_straight.smoothness_score)

    def test_ablation_config_presets(self):
        full = AblationConfig.get_preset("FULL")
        self.assertTrue(full.enable_future_risk)
        self.assertTrue(full.enable_uncertainty)

        no_risk = AblationConfig.get_preset("WITHOUT_FUTURE_RISK")
        self.assertFalse(no_risk.enable_future_risk)

        no_unc = AblationConfig.get_preset("WITHOUT_UNCERTAINTY")
        self.assertFalse(no_unc.enable_uncertainty)

    def test_benchmark_comparator(self):
        sample_results = [
            {
                "scenario_id": "UNMARKED_VILLAGE_ROAD",
                "planner_mode": "BASELINE_ASTAR",
                "completion_rate": 1.0,
                "collision_count": 0,
                "min_clearance_meters": 1.5,
                "peak_risk": 0.25,
                "smoothness_score": 0.85
            },
            {
                "scenario_id": "UNMARKED_VILLAGE_ROAD",
                "planner_mode": "IRIS_FULL",
                "completion_rate": 1.0,
                "collision_count": 0,
                "min_clearance_meters": 2.1,
                "peak_risk": 0.12,
                "smoothness_score": 0.94
            }
        ]
        comp = BenchmarkComparator.generate_comparison_matrix(sample_results)
        self.assertEqual(comp["scenarios_evaluated"], 1)

        formatted_text = BenchmarkComparator.format_text_table(comp)
        self.assertIn("UNMARKED_VILLAGE_ROAD", formatted_text)
        self.assertIn("IRIS_FULL", formatted_text)

    def test_report_generator(self):
        rep_gen = ReportGenerator(output_dir=self.test_out_dir)
        json_path = rep_gen.save_json_report({"test_key": "test_val"}, "test.json")
        self.assertTrue(os.path.exists(json_path))

        csv_path = rep_gen.save_csv_report([{"col1": "val1", "col2": 2}], "test.csv")
        self.assertTrue(os.path.exists(csv_path))

        comp_data = {
            "scenarios_evaluated": 1,
            "comparison_matrix": {
                "TEST_SCENARIO": {
                    "FULL": {
                        "completion_rate": 1.0,
                        "collision_count": 0,
                        "near_collision_count": 0,
                        "min_clearance_m": 2.0,
                        "min_ttc_s": 5.0,
                        "peak_risk": 0.1,
                        "average_risk": 0.05,
                        "smoothness_score": 0.9,
                        "replan_count": 1,
                        "avg_replan_latency_ms": 12.5
                    }
                }
            }
        }
        html_path = rep_gen.generate_html_summary(comp_data, "test_summary.html")
        self.assertTrue(os.path.exists(html_path))

        plots_path = rep_gen.generate_plots({"risk": [0.1, 0.2, 0.15], "speed": [5.0, 6.0, 7.0]}, "test_plots.png")
        self.assertTrue(os.path.exists(plots_path))

    def test_experiment_runner_single(self):
        runner = ExperimentRunner(output_dir=self.test_out_dir, seed=42)
        res = runner.run_single_experiment("SUDDEN_CATTLE_CROSSING", "FULL", duration=1.0)
        self.assertIn("result_dict", res)
        self.assertEqual(res["result_dict"]["scenario_id"], "SUDDEN_CATTLE_CROSSING")


if __name__ == "__main__":
    unittest.main()
