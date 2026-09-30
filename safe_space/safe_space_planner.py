"""
IRIS Safe-Space Planner Facade (Phase 11).
Orchestrates SafeSpaceAnalyzer, CandidateGenerator, and CandidateScorer to select the safest
practical candidate corridor/path through drivable negative space.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
import numpy as np

from world.world_model import WorldModel
from planning.astar import AStarPlanner
from planning.path import Path
from future_risk.future_risk_field import FutureRiskField

from safe_space.config import PLANNER_MODE, LOCAL_PLANNING_RADIUS
from safe_space.corridor import SafeCorridor
from safe_space.safe_space_analyzer import SafeSpaceAnalyzer, SafeSpaceMap
from safe_space.candidate_generator import CandidateGenerator
from safe_space.candidate_scorer import CandidateScorer


@dataclass
class PlanningResult:
    """
    Structured outcome of SafeSpacePlanner execution.
    """
    success: bool
    selected_path: Optional[Path] = None
    selected_corridor: Optional[SafeCorridor] = None
    candidate_paths: List[SafeCorridor] = field(default_factory=list)
    candidate_scores: List[float] = field(default_factory=list)
    reason: str = "NO_SAFE_CORRIDOR"
    metrics: Dict[str, Any] = field(default_factory=dict)
    safe_space_map: Optional[SafeSpaceMap] = None


class SafeSpacePlanner:
    """
    High-level facade for IRIS Safe-Space / Negative-Space Planning.
    """

    def __init__(self, mode: str = PLANNER_MODE):
        self.mode = mode
        self.analyzer = SafeSpaceAnalyzer()
        self.generator = CandidateGenerator()
        self.scorer = CandidateScorer()
        self.baseline_planner = AStarPlanner(allow_diagonal=False)
        self.last_result: Optional[PlanningResult] = None

    def plan(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        start_pos: Optional[Tuple[float, float]] = None,
        goal_pos: Optional[Tuple[float, float]] = None,
    ) -> PlanningResult:
        """
        Plans a path connecting start_pos and goal_pos using configured planner mode.
        """
        converter = world_model.converter
        if start_pos is None:
            # Fallback: Ego vehicle current position
            ego = world_model.ego_state
            def_start = converter.sim_to_world(5.0, 0.0)
            start_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))
        if goal_pos is None:
            goal_pos = world_model.goal_position

        # Clip goal position to LOCAL_PLANNING_RADIUS horizon if far away
        if goal_pos[0] - start_pos[0] > LOCAL_PLANNING_RADIUS:
            goal_pos = (start_pos[0] + LOCAL_PLANNING_RADIUS, goal_pos[1])

        # 1. Mode 1: Baseline A* Planner (Traversability Only)
        if self.mode == "baseline_astar":
            planned_path = self.baseline_planner.plan(start_pos, goal_pos, world_model)
            corridor = None
            if planned_path.success:
                corridor = SafeCorridor(
                    corridor_id="BASELINE_ASTAR_01",
                    name="BASELINE_ASTAR",
                    centerline=list(planned_path.world_points),
                    grid_cells=list(planned_path.grid_points),
                    length=planned_path.length,
                    is_valid=True,
                    total_score=planned_path.length,
                )

            res = PlanningResult(
                success=planned_path.success,
                selected_path=planned_path,
                selected_corridor=corridor,
                candidate_paths=[corridor] if corridor else [],
                candidate_scores=[planned_path.length] if planned_path.success else [],
                reason="baseline_astar_mode" if planned_path.success else "baseline_astar_failed",
                metrics={"mode": "baseline_astar", "path_cost": planned_path.length},
            )
            self.last_result = res
            return res

        # 2. Mode 2: IRIS Safe-Space Planner (Negative Space + Future Risk + Clearance + Costs)
        # Step A: Perform Safe-Space Analysis & Clearance Transform
        space_map = self.analyzer.analyze(world_model, future_risk_field)

        # Step B: Generate Candidate Corridors
        raw_candidates = self.generator.generate_candidates(start_pos, goal_pos, world_model, space_map.clearance_grid)

        # Step C: Evaluate Hard Constraints & Multi-Objective Soft Costs for each Candidate
        evaluated_candidates: List[SafeCorridor] = []
        candidate_scores: List[float] = []

        for cand in raw_candidates:
            eval_cand = self.scorer.evaluate_candidate(
                corridor=cand,
                world_model=world_model,
                future_risk_field=future_risk_field,
                clearance_map=self.analyzer.clearance_model,
                goal_pos=goal_pos,
            )
            evaluated_candidates.append(eval_cand)
            candidate_scores.append(eval_cand.total_score)

        # Attach candidates to SafeSpaceMap
        space_map.candidate_corridors = evaluated_candidates

        # Step D: Filter valid candidates and select candidate with lowest cost score
        valid_candidates = [c for c in evaluated_candidates if c.is_valid]

        if not valid_candidates:
            # NO_SAFE_CORRIDOR condition: No candidate passed hard safety constraints
            res = PlanningResult(
                success=False,
                selected_path=None,
                selected_corridor=None,
                candidate_paths=evaluated_candidates,
                candidate_scores=candidate_scores,
                reason="NO_SAFE_CORRIDOR",
                metrics={
                    "mode": "iris_safe_space",
                    "total_candidates": len(evaluated_candidates),
                    "valid_candidates": 0,
                    "rejection_reasons": [c.rejection_reason for c in evaluated_candidates],
                },
                safe_space_map=space_map,
            )
            self.last_result = res
            return res

        # Sort valid candidates by score ascending (lowest-cost candidate selected)
        valid_candidates.sort(key=lambda c: c.total_score)
        best_corridor = valid_candidates[0]
        space_map.selected_corridor = best_corridor

        # Construct Path object from selected candidate centerline
        selected_path = Path(
            world_points=best_corridor.centerline,
            grid_points=best_corridor.grid_cells,
            length=best_corridor.length,
            valid=True,
            success=True,
            status_message=f"Selected {best_corridor.corridor_id} ({best_corridor.name}) - Score: {best_corridor.total_score:.2f}",
        )

        res = PlanningResult(
            success=True,
            selected_path=selected_path,
            selected_corridor=best_corridor,
            candidate_paths=evaluated_candidates,
            candidate_scores=candidate_scores,
            reason="lowest_cost_valid_candidate",
            metrics={
                "mode": "iris_safe_space",
                "total_candidates": len(evaluated_candidates),
                "valid_candidates": len(valid_candidates),
                "selected_id": best_corridor.corridor_id,
                "selected_score": best_corridor.total_score,
                "selected_length": best_corridor.length,
                "selected_min_clearance": best_corridor.min_clearance,
                "selected_peak_risk": best_corridor.peak_risk,
                "selected_avg_risk": best_corridor.avg_risk,
            },
            safe_space_map=space_map,
        )
        self.last_result = res
        return res
