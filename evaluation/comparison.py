"""
IRIS Baseline & Ablation Comparison Module (Combined Phase 15).
Generates side-by-side metric comparison tables showing measured differences between baseline planners and IRIS ablation modes.
"""

from typing import List, Dict, Any, Optional
import json


class BenchmarkComparator:
    """
    Builds quantitative comparative summary tables without bias or auto-winner declaration.
    """

    @staticmethod
    def generate_comparison_matrix(results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Group metrics by scenario and mode/config, producing comparison tables.
        """
        scenarios: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for res in results_list:
            sc_id = res.get("scenario_id", "UNKNOWN")
            mode = res.get("planner_mode", res.get("configuration_name", "UNKNOWN"))

            if sc_id not in scenarios:
                scenarios[sc_id] = {}

            scenarios[sc_id][mode] = {
                "completion_rate": res.get("completion_rate", 0.0),
                "collision_count": res.get("collision_count", 0),
                "near_collision_count": res.get("near_collision_count", 0),
                "min_clearance_m": round(res.get("min_clearance_meters", 0.0), 2),
                "min_ttc_s": round(res.get("min_ttc_seconds", 0.0), 2),
                "peak_risk": round(res.get("peak_risk", 0.0), 3),
                "average_risk": round(res.get("average_risk", 0.0), 3),
                "total_path_length_m": round(res.get("total_path_length", 0.0), 2),
                "travel_time_s": round(res.get("total_travel_time", 0.0), 2),
                "smoothness_score": round(res.get("smoothness_score", 0.0), 3),
                "replan_count": res.get("replan_count", 0),
                "avg_replan_latency_ms": round(res.get("avg_replan_latency_ms", 0.0), 2),
            }

        return {
            "scenarios_evaluated": len(scenarios),
            "comparison_matrix": scenarios
        }

    @staticmethod
    def format_text_table(comparison_data: Dict[str, Any]) -> str:
        """
        Format comparison matrix into human-readable text table.
        """
        matrix = comparison_data.get("comparison_matrix", {})
        lines = []
        lines.append("=" * 115)
        lines.append("IRIS QUANTITATIVE BENCHMARK COMPARISON MATRIX (MEASURED DIFFERENCES)")
        lines.append("=" * 115)

        header = f"{'Scenario ID':<26} | {'Mode/Config':<20} | {'Compl':<6} | {'Coll':<5} | {'Near C':<6} | {'Clear(m)':<8} | {'Risk(Pk)':<8} | {'Smooth':<6} | {'Replan':<6} | {'Lat(ms)':<7}"
        lines.append(header)
        lines.append("-" * 115)

        for sc_id, modes in matrix.items():
            for mode_name, m in modes.items():
                row = (
                    f"{sc_id:<26} | {mode_name:<20} | "
                    f"{m['completion_rate']*100:>5.0f}% | "
                    f"{m['collision_count']:>5d} | "
                    f"{m['near_collision_count']:>6d} | "
                    f"{m['min_clearance_m']:>8.2f} | "
                    f"{m['peak_risk']:>8.3f} | "
                    f"{m['smoothness_score']:>6.3f} | "
                    f"{m['replan_count']:>6d} | "
                    f"{m['avg_replan_latency_ms']:>7.2f}"
                )
                lines.append(row)
            lines.append("-" * 115)

        lines.append("=" * 115)
        return "\n".join(lines)
