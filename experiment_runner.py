"""
IRIS Experiment & Benchmark Matrix Runner (Combined Phase 15).
Executes reproducible scenario matrix runs across Baseline Planners and Ablation Configurations,
saving structured JSON, CSV tables, HTML summary reports, and visual telemetry PNG plots.
"""

import os
import sys
import math
import json
import time
import argparse
from typing import List, Dict, Any, Optional

from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from scenarios.scenario_loader import ScenarioRegistry
from scenarios.scenario_runner import ScenarioRunner
from replanning.replanning_manager import ReplanningManager
from evaluation.scenario_metrics import ScenarioMetricsTracker, ExtendedScenarioMetrics
from evaluation.ablation_config import AblationConfig
from evaluation.comparison import BenchmarkComparator
from evaluation.report import ReportGenerator


class ExperimentRunner:
    """
    Automated benchmark matrix runner for baseline and ablation evaluations.
    """

    BASELINE_MODES = [
        "BASELINE_ASTAR",
        "IRIS_SAFE_SPACE",
        "IRIS_ADAPTIVE",
        "IRIS_FULL",
    ]

    ABLATION_PRESETS = [
        "FULL",
        "WITHOUT_FUTURE_RISK",
        "WITHOUT_UNCERTAINTY",
        "WITHOUT_SAFE_SPACE",
        "WITHOUT_SURFACE_COST",
        "WITHOUT_ADAPTIVE_REPLANNING",
    ]

    def __init__(self, output_dir: str = "experiment_results", seed: int = 42):
        self.output_dir = output_dir
        self.seed = seed
        self.registry = ScenarioRegistry()
        self.scenario_runner = ScenarioRunner(registry=self.registry)
        self.report_gen = ReportGenerator(output_dir=self.output_dir)

    def run_single_experiment(self, scenario_id: str, mode_or_preset: str,
                              duration: float = 10.0, dt: float = 0.05) -> Dict[str, Any]:
        """
        Execute a single scenario under a specified baseline or ablation mode.
        """
        # Determine if baseline mode or ablation preset
        ablation_cfg = AblationConfig.get_preset(mode_or_preset)

        env = SimulationEnvironment()
        world_model = WorldModel()

        scenario = self.scenario_runner.load_scenario(scenario_id, seed=self.seed)
        if not scenario:
            raise ValueError(f"Unknown scenario ID: {scenario_id}")

        self.scenario_runner.initialize_environment(env)
        tracker = ScenarioMetricsTracker(
            scenario_id=scenario_id,
            planner_mode=mode_or_preset,
            config_name=ablation_cfg.name,
            seed=self.seed
        )

        replanning_mgr = ReplanningManager()

        # Apply ablation config to candidate scorer if present
        if hasattr(replanning_mgr, "safe_space_planner") and replanning_mgr.safe_space_planner:
            if hasattr(replanning_mgr.safe_space_planner, "scorer"):
                replanning_mgr.safe_space_planner.scorer.apply_ablation_config(ablation_cfg)

        steps = int(duration / dt)
        hist_time = []
        hist_risk = []
        hist_speed = []
        hist_clr = []

        from perception.perception_manager import PerceptionManager
        from perception.simulated_detector import SimulatedDetector
        from tracking.track_manager import TrackManager
        from prediction.prediction_manager import PredictionManager
        from uncertainty.uncertainty_manager import UncertaintyManager
        from future_risk.future_risk_engine import FutureRiskEngine

        perception_mgr = PerceptionManager(detector=SimulatedDetector())
        track_mgr = TrackManager()
        pred_mgr = PredictionManager()
        unc_mgr = UncertaintyManager()
        risk_eng = FutureRiskEngine()

        for step in range(steps):
            env.step(dt, 0.0, 0.0)
            detections = perception_mgr.process(env)
            tracks = track_mgr.update(detections, timestamp=env.sim_time)
            prediction_set = pred_mgr.predict(tracks, timestamp=env.sim_time, road_evaluator=world_model.is_drivable_at_world)
            uncertainty_set = unc_mgr.evaluate_uncertainty(tracks, prediction_set, current_time=env.sim_time)
            world_model.update_from_environment(
                env,
                perception_manager=perception_mgr,
                track_manager=track_mgr,
                prediction_manager=pred_mgr,
                prediction_set=prediction_set,
                uncertainty_manager=unc_mgr,
                uncertainty_set=uncertainty_set,
                future_risk_engine=risk_eng,
            )

            # Replanning check if adaptive replanning enabled
            if ablation_cfg.enable_adaptive_replanning:
                start_pos = world_model.converter.sim_to_world(env.ego_vehicle.x, env.ego_vehicle.y)
                replanning_mgr.update(
                    sim_time=env.sim_time,
                    ego_pos=start_pos,
                    goal_pos=world_model.goal_position,
                    world_model=world_model,
                    future_risk_field=world_model.future_risk_field,
                )

            tracker.update_step(env, world_model, replanning_mgr, dt=dt)

            # Record telemetry sample
            hist_time.append(env.sim_time)
            hist_risk.append(tracker.metrics.peak_risk)
            hist_speed.append(env.ego_vehicle.velocity)
            hist_clr.append(env.get_minimum_clearance())

            if tracker.metrics.scenario_completed:
                break

        final_metrics = tracker.finalize()
        result_dict = final_metrics.to_dict()

        # Save to experiment_results/<scenario_name>/<mode>.json
        sc_dir = os.path.join(self.output_dir, scenario_id.lower())
        os.makedirs(sc_dir, exist_ok=True)
        out_json = os.path.join(sc_dir, f"{mode_or_preset.lower()}.json")
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(result_dict, f, indent=2)

        return {
            "result_dict": result_dict,
            "telemetry": {
                "time": hist_time,
                "risk": hist_risk,
                "speed": hist_speed,
                "clearance": hist_clr
            }
        }

    def run_matrix_suite(self, scenarios: Optional[List[str]] = None,
                         modes: Optional[List[str]] = None,
                         duration: float = 8.0) -> Dict[str, Any]:
        """
        Run matrix benchmark suite across multiple scenarios and modes/ablations.
        """
        if scenarios is None:
            scenarios = [
                "UNMARKED_VILLAGE_ROAD",
                "UNSIGNALIZED_URBAN_INTERSECTION",
                "HIGHWAY_MERGE",
                "DENSE_MARKET",
                "SUDDEN_CATTLE_CROSSING",
            ]

        if modes is None:
            modes = self.BASELINE_MODES + self.ABLATION_PRESETS[1:]

        all_results = []
        sample_telemetry = {}

        print(f"[IRIS ExperimentRunner] Executing Benchmark Matrix: {len(scenarios)} scenarios x {len(modes)} modes...")
        sys.stdout.flush()

        for sc in scenarios:
            for m in modes:
                print(f"  -> Running Scenario '{sc}' | Mode: '{m}' ...")
                sys.stdout.flush()
                res = self.run_single_experiment(sc, m, duration=duration)
                all_results.append(res["result_dict"])
                if not sample_telemetry:
                    sample_telemetry = res["telemetry"]

        # Build comparison summary
        comp_data = BenchmarkComparator.generate_comparison_matrix(all_results)
        text_table = BenchmarkComparator.format_text_table(comp_data)
        print("\n" + text_table + "\n")

        # Save machine-readable JSON summary, CSV, HTML, and Plots
        self.report_gen.save_json_report(comp_data, "comparison_summary.json")
        self.report_gen.save_csv_report(all_results, "metrics_matrix.csv")
        self.report_gen.generate_html_summary(comp_data, "summary_report.html")

        if sample_telemetry:
            self.report_gen.generate_plots(sample_telemetry, "telemetry_plots.png")

        print(f"[IRIS ExperimentRunner] Matrix execution complete. All reports saved to '{self.output_dir}/'.")
        return comp_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRIS Benchmark & Experiment Matrix Runner")
    parser.add_argument("--scenario", type=str, default=None, help="Scenario ID (default: all mandatory)")
    parser.add_argument("--mode", type=str, default=None, help="Planner mode or ablation preset")
    parser.add_argument("--seed", type=int, default=42, help="Configurable random seed")
    parser.add_argument("--duration", type=float, default=8.0, help="Simulation duration (s)")
    parser.add_argument("--outdir", type=str, default="experiment_results", help="Output directory")

    args = parser.parse_args()
    runner = ExperimentRunner(output_dir=args.outdir, seed=args.seed)

    if args.scenario and args.mode:
        runner.run_single_experiment(args.scenario, args.mode, duration=args.duration)
    else:
        scs = [args.scenario] if args.scenario else None
        mds = [args.mode] if args.mode else None
        runner.run_matrix_suite(scenarios=scs, modes=mds, duration=args.duration)
