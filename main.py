"""
IRIS — Indian Road Intelligence & Safe-space Planner
Central Entry Point (Unified 16-Phase System Integration).

Tagline: "Predict the road before the road becomes dangerous."

Usage:
  python main.py                                      # Default IRIS run
  python main.py --scenario cattle                    # Specific scenario (cattle, village, market, etc.)
  python main.py --planner astar                      # Run Phase 3 A* Baseline Planner
  python main.py --planner iris                       # Run Full IRIS Safe-Space Engine
  python main.py --mode demo                          # Run 3:30 Competition Presentation Demo
  python main.py --mode evaluation                    # Run full baseline & ablation experiment matrix
"""

import os
import sys
import argparse

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.iris_system import IRISSystem


def main():
    parser = argparse.ArgumentParser(
        description="IRIS — Indian Road Intelligence & Safe-space Planner (Unified 16-Phase Autonomous System)"
    )
    parser.add_argument("--scenario", type=str, default="SUDDEN_CATTLE_CROSSING",
                        help="Scenario ID (village, intersection, highway, market, cattle, pothole, waterlogging, combined, etc.)")
    parser.add_argument("--planner", type=str, default="iris", choices=["iris", "astar"],
                        help="Planner choice: 'iris' (Safe-Space + Risk Field) or 'astar' (Phase 3 A* Baseline)")
    parser.add_argument("--mode", type=str, default="simulation", choices=["simulation", "demo", "evaluation"],
                        help="Run mode: 'simulation' (live dashboard), 'demo' (3:30 video sequence), 'evaluation' (matrix benchmark)")
    parser.add_argument("--seed", type=int, default=42, help="Configurable random seed for reproducibility")
    parser.add_argument("--duration", type=float, default=30.0, help="Scenario duration limit in seconds")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode without GUI dashboard")
    parser.add_argument("--debug", action="store_true", help="Enable debug telemetry overlays")

    args = parser.parse_args()

    # Normalize alias names for scenarios
    scenario_alias_map = {
        "village": "UNMARKED_VILLAGE_ROAD",
        "intersection": "UNSIGNALIZED_URBAN_INTERSECTION",
        "highway": "HIGHWAY_MERGE",
        "market": "DENSE_MARKET",
        "cattle": "SUDDEN_CATTLE_CROSSING",
        "pothole": "POTHOLE_AVOIDANCE",
        "waterlogging": "WATERLOGGING",
        "combined": "COMBINED_SURFACE_HAZARDS",
    }
    sc_name = args.scenario.lower()
    if sc_name in scenario_alias_map:
        args.scenario = scenario_alias_map[sc_name]

    print("==========================================================================")
    print("IRIS -- Indian Road Intelligence & Safe-Space Planner")
    print("Tagline: 'Predict the road before the road becomes dangerous.'")
    print("==========================================================================")
    print(f"Mode: {args.mode.upper()} | Scenario: {args.scenario} | Planner: {args.planner.upper()} | Seed: {args.seed}")
    print("==========================================================================\n")

    # 1. Demo Mode Execution
    if args.mode == "demo":
        print("[IRIS Main] Launching Automated Competition Demonstration Pipeline...")
        from demo.demo_runner import DemoRunner
        demo_runner = DemoRunner(seed=args.seed, headless=args.headless)
        demo_runner.run_demo_sequence()
        sys.exit(0)

    # 2. Evaluation Mode Execution
    if args.mode == "evaluation":
        print("[IRIS Main] Launching Benchmark & Experiment Matrix Suite...")
        from experiment_runner import ExperimentRunner
        runner = ExperimentRunner(seed=args.seed)
        runner.run_matrix_suite(duration=min(10.0, args.duration))
        sys.exit(0)

    # 3. Standard Integrated Simulation Execution (Phases 1-16 Connected)
    config_dict = {
        "scenario": args.scenario,
        "planner": args.planner,
        "mode": args.mode,
        "seed": args.seed,
        "duration": args.duration,
        "headless": args.headless,
        "debug": args.debug
    }

    system = IRISSystem(config=config_dict)
    system.initialize()
    system.run()

    sys.exit(0)


if __name__ == "__main__":
    main()
