"""
IRIS Candidate Scorer (Phase 11).
Evaluates candidate safe corridors against Hard Safety Constraints (vehicle clearance, non-traversable cells)
and computes Soft Multi-Objective Cost Scores (future risk, clearance, surface hazards, boundary proximity,
length, smoothness, prediction uncertainty, and goal distance).
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Any

from world.world_model import WorldModel
from world.cell import CellState
from future_risk.future_risk_field import FutureRiskField
from safe_space.corridor import SafeCorridor
from safe_space.clearance import ClearanceMap
from safe_space.config import (
    VEHICLE_WIDTH,
    VEHICLE_SAFETY_MARGIN,
    MIN_CORRIDOR_WIDTH,
    RISK_COST_WEIGHT,
    CLEARANCE_COST_WEIGHT,
    LENGTH_COST_WEIGHT,
    SMOOTHNESS_COST_WEIGHT,
    SURFACE_COST_WEIGHT,
    BOUNDARY_COST_WEIGHT,
    UNCERTAINTY_COST_WEIGHT,
    GOAL_COST_WEIGHT,
    CANDIDATE_SAMPLE_DISTANCE,
    NOMINAL_PLANNING_SPEED,
)


class CandidateScorer:
    """
    Evaluates hard safety constraints and soft multi-objective cost scores for candidate corridors.
    """

    def __init__(
        self,
        w_risk: float = RISK_COST_WEIGHT,
        w_clearance: float = CLEARANCE_COST_WEIGHT,
        w_length: float = LENGTH_COST_WEIGHT,
        w_smoothness: float = SMOOTHNESS_COST_WEIGHT,
        w_surface: float = SURFACE_COST_WEIGHT,
        w_boundary: float = BOUNDARY_COST_WEIGHT,
        w_uncertainty: float = UNCERTAINTY_COST_WEIGHT,
        w_goal: float = GOAL_COST_WEIGHT,
        vehicle_margin: float = VEHICLE_SAFETY_MARGIN,
    ):
        self.w_risk = w_risk
        self.w_clearance = w_clearance
        self.w_length = w_length
        self.w_smoothness = w_smoothness
        self.w_surface = w_surface
        self.w_boundary = w_boundary
        self.w_uncertainty = w_uncertainty
        self.w_goal = w_goal
        self.required_clearance = (VEHICLE_WIDTH + vehicle_margin) / 2.0  # e.g., 1.1m

    def apply_ablation_config(self, ablation_cfg: Any):
        """Apply feature toggles from AblationConfig."""
        if hasattr(ablation_cfg, "enable_future_risk") and not ablation_cfg.enable_future_risk:
            self.w_risk = 0.0
        if hasattr(ablation_cfg, "enable_uncertainty") and not ablation_cfg.enable_uncertainty:
            self.w_uncertainty = 0.0
        if hasattr(ablation_cfg, "enable_surface_cost") and not ablation_cfg.enable_surface_cost:
            self.w_surface = 0.0
        if hasattr(ablation_cfg, "enable_clearance_cost") and not ablation_cfg.enable_clearance_cost:
            self.w_clearance = 0.0
        if hasattr(ablation_cfg, "enable_boundary_cost") and not ablation_cfg.enable_boundary_cost:
            self.w_boundary = 0.0
        if hasattr(ablation_cfg, "enable_smoothness_cost") and not ablation_cfg.enable_smoothness_cost:
            self.w_smoothness = 0.0

    def evaluate_candidate(
        self,
        corridor: SafeCorridor,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField],
        clearance_map: ClearanceMap,
        goal_pos: Tuple[float, float],
    ) -> SafeCorridor:
        """
        Evaluates hard constraints and soft cost components for a candidate corridor.
        Mutates `corridor` fields in-place and returns the updated `SafeCorridor`.
        """
        if not corridor.centerline or len(corridor.centerline) < 2:
            corridor.is_valid = False
            corridor.rejection_reason = "Empty or trivial candidate path"
            corridor.total_score = 999.0
            return corridor

        grid = world_model.grid
        converter = world_model.converter
        clearance_grid = clearance_map.clearance_grid

        # 1. Resample candidate path at uniform spatial distance steps
        sampled_pts, accum_dists = self._resample_path(corridor.centerline, CANDIDATE_SAMPLE_DISTANCE)
        num_pts = len(sampled_pts)

        if num_pts == 0:
            corridor.is_valid = False
            corridor.rejection_reason = "Resampling yielded zero points"
            corridor.total_score = 999.0
            return corridor

        # 2. Hard Constraint Evaluation & Per-point Property Sampling
        min_clearance = 999.0
        clearances = []
        risks = []
        surfaces = []
        boundaries = []
        uncertainties = []

        is_valid = True
        rejection_reason = ""

        for idx, (px, py) in enumerate(sampled_pts):
            r, c = converter.world_to_grid(px, py)
            cell = grid.get_cell_at_world(px, py)

            # Check Hard Constraint A: Cell must exist and be drivable (allow start cell / VEHICLE state for ego)
            if cell is None or (not cell.is_drivable and cell.state != CellState.VEHICLE and idx > 0):
                is_valid = False
                rejection_reason = f"Hits non-traversable cell at index {idx} ({px:.1f}, {py:.1f})"
                break

            # Check Hard Constraint B: State cannot be OUTSIDE_ROAD, ROAD_BOUNDARY, or OCCUPIED (allow VEHICLE at idx 0)
            if cell.state in (CellState.OUTSIDE_ROAD, CellState.ROAD_BOUNDARY) or (cell.state == CellState.OCCUPIED and idx > 0):
                is_valid = False
                rejection_reason = f"Traverses non-traversable state {cell.state.name} at ({px:.1f}, {py:.1f})"
                break

            # Sample Clearance
            c_val = clearance_grid[r, c] if clearance_grid is not None else 1.0
            clearances.append(c_val)
            min_clearance = min(min_clearance, c_val)

            # Check Hard Constraint C: Minimum required vehicle physical clearance
            if c_val < self.required_clearance:
                is_valid = False
                rejection_reason = f"Insufficient vehicle clearance ({c_val:.2f}m < {self.required_clearance:.2f}m)"
                break

            # Sample Temporal Future Risk at estimated arrival time t = distance / v_nominal
            travel_dist = accum_dists[idx]
            travel_time = travel_dist / max(1.0, NOMINAL_PLANNING_SPEED)

            if future_risk_field is not None:
                r_val = future_risk_field.get_risk_at_time(travel_time, (px, py), converter)
            else:
                r_val = 0.0
            risks.append(r_val)

            # Sample Surface Severity
            s_val = getattr(cell, "surface_severity", 0.0)
            surfaces.append(s_val)

            # Sample Boundary Distance / Proximity
            dist_left = abs(py - (converter.lateral_offset + converter.road_width / 2.0))
            dist_right = abs(py - (converter.lateral_offset - converter.road_width / 2.0))
            edge_dist = min(dist_left, dist_right)
            # Boundary cost increases near road edge (< 1.5m)
            b_val = math.exp(-0.8 * max(0.0, edge_dist))
            boundaries.append(b_val)

            # Sample Phase 9 Uncertainty
            u_val = 0.0
            if hasattr(world_model, "uncertainty_grid") and world_model.uncertainty_grid is not None:
                u_val = world_model.uncertainty_grid.get_uncertainty_at_world(px, py, converter)
            uncertainties.append(u_val)

        if not is_valid:
            corridor.is_valid = False
            corridor.rejection_reason = rejection_reason
            corridor.min_clearance = min_clearance if min_clearance < 900.0 else 0.0
            corridor.total_score = 999.0
            return corridor

        # 3. Soft Multi-Objective Cost Calculations
        corridor.is_valid = True
        corridor.rejection_reason = "Valid safe corridor"
        corridor.min_clearance = float(min_clearance)
        corridor.avg_clearance = float(np.mean(clearances))
        corridor.width = float(2.0 * min_clearance)

        # Risk Metrics
        if risks and max(risks) > 0.0:
            corridor.avg_risk = float(np.mean(risks))
            corridor.peak_risk = float(np.max(risks))
            corridor.risk_integral = float(np.sum(risks) * CANDIDATE_SAMPLE_DISTANCE)

        # Cost Components (normalized ~ [0.0, 1.0])
        cost_risk = 0.7 * corridor.avg_risk + 0.3 * corridor.peak_risk
        cost_clearance = float(np.mean([1.0 / max(0.1, c_val) for c_val in clearances])) / 10.0
        cost_surface = float(np.mean(surfaces)) if surfaces else 0.0
        cost_boundary = float(np.mean(boundaries)) if boundaries else 0.0
        cost_length = min(1.0, corridor.length / 80.0)
        cost_smoothness = self._calculate_smoothness_cost(sampled_pts)
        cost_uncertainty = float(np.mean(uncertainties)) if uncertainties else 0.0

        # Goal Distance Cost
        end_pt = sampled_pts[-1]
        dist_to_goal = math.hypot(end_pt[0] - goal_pos[0], end_pt[1] - goal_pos[1])
        cost_goal = min(1.0, dist_to_goal / 50.0)

        # Store Cost Component Breakdown
        corridor.surface_cost = cost_surface
        corridor.boundary_cost = cost_boundary
        corridor.smoothness_cost = cost_smoothness
        corridor.clearance_cost = cost_clearance
        corridor.length_cost = cost_length
        corridor.uncertainty_cost = cost_uncertainty
        corridor.goal_cost = cost_goal

        # Total Weighted Multi-Objective Score
        total_score = (
            self.w_risk * cost_risk +
            self.w_clearance * cost_clearance +
            self.w_surface * cost_surface +
            self.w_boundary * cost_boundary +
            self.w_length * cost_length +
            self.w_smoothness * cost_smoothness +
            self.w_uncertainty * cost_uncertainty +
            self.w_goal * cost_goal
        )
        corridor.total_score = float(total_score)
        return corridor

    def _resample_path(
        self,
        centerline: List[Tuple[float, float]],
        sample_step: float,
    ) -> Tuple[List[Tuple[float, float]], List[float]]:
        """Resamples path points at uniform linear distance intervals."""
        if not centerline:
            return [], []

        sampled = [centerline[0]]
        accum_dists = [0.0]
        total_dist = 0.0

        for i in range(len(centerline) - 1):
            p1, p2 = centerline[i], centerline[i + 1]
            seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if seg_len < 1e-4:
                continue

            num_steps = int(math.ceil(seg_len / sample_step))
            for s in range(1, num_steps + 1):
                alpha = s / float(num_steps)
                rx = p1[0] + alpha * (p2[0] - p1[0])
                ry = p1[1] + alpha * (p2[1] - p1[1])
                d_inc = alpha * seg_len
                sampled.append((rx, ry))
                accum_dists.append(total_dist + d_inc)

            total_dist += seg_len

        return sampled, accum_dists

    def _calculate_smoothness_cost(self, points: List[Tuple[float, float]]) -> float:
        """Calculates path geometric smoothness cost based on cumulative absolute heading changes."""
        if len(points) < 3:
            return 0.0

        total_heading_change = 0.0
        for i in range(len(points) - 2):
            p1, p2, p3 = points[i], points[i + 1], points[i + 2]
            h1 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
            h2 = math.atan2(p3[1] - p2[1], p3[0] - p2[0])
            dh = abs(math.atan2(math.sin(h2 - h1), math.cos(h2 - h1)))
            total_heading_change += dh

        # Normalize over path length
        return min(1.0, total_heading_change / (math.pi * 2.0))
