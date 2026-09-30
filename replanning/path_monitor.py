"""
IRIS Path Monitor (Phase 12).
Continuously evaluates active planned path against latest WorldModel, FutureRiskField,
Uncertainty, SurfaceModel, and ego vehicle progress. Calculates path validity, path degradation,
peak future risk, minimum clearance, blocked cell count, and path deviation.
"""

import math
import numpy as np
from typing import Tuple, Optional, Any

from world.world_model import WorldModel
from world.cell import CellState
from future_risk.future_risk_field import FutureRiskField
from safe_space.config import VEHICLE_WIDTH, VEHICLE_SAFETY_MARGIN, NOMINAL_PLANNING_SPEED
from replanning.config import (
    RISK_REPLAN_THRESHOLD,
    PEAK_RISK_INCREASE_THRESHOLD,
    MIN_CLEARANCE_THRESHOLD,
    HARD_CLEARANCE_THRESHOLD,
    PATH_DEVIATION_THRESHOLD,
)
from replanning.path_state import CurrentPathState


class PathMonitor:
    """
    Monitors active path health, safety, risk evolution, clearance, and traversability.
    """

    def __init__(self, required_clearance: float = (VEHICLE_WIDTH + VEHICLE_SAFETY_MARGIN) / 2.0):
        self.required_clearance = required_clearance

    def monitor_path(
        self,
        path_state: CurrentPathState,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        ego_pos: Optional[Tuple[float, float]] = None,
    ) -> CurrentPathState:
        """
        Evaluates current active path against current world state and future risk field.
        Mutates and returns `path_state`.
        """
        if path_state.path is None or not path_state.path.world_points or not getattr(path_state.path, "valid", True):
            path_state.path_valid = False
            path_state.path_degraded = True
            return path_state

        converter = world_model.converter
        grid = world_model.grid

        # 1. Update Ego Vehicle Waypoint Progress & Remaining Distance
        if ego_pos is None:
            ego = world_model.ego_state
            def_start = converter.sim_to_world(5.0, 0.0)
            ego_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))

        ego_x, ego_y = ego_pos
        world_pts = path_state.path.world_points
        num_pts = len(world_pts)

        # Advance current waypoint index
        curr_idx = path_state.current_waypoint_index
        while curr_idx < num_pts - 1:
            wx, wy = world_pts[curr_idx]
            if math.hypot(wx - ego_x, wy - ego_y) < 2.5:
                curr_idx += 1
            else:
                break
        path_state.current_waypoint_index = curr_idx

        # Calculate remaining distance from active waypoint
        rem_dist = 0.0
        for i in range(curr_idx, num_pts - 1):
            x1, y1 = world_pts[i]
            x2, y2 = world_pts[i + 1]
            rem_dist += math.hypot(x2 - x1, y2 - y1)
        path_state.remaining_distance = rem_dist

        # 2. Calculate Path Deviation from Ego Position
        min_dev = 999.0
        for wx, wy in world_pts[curr_idx:]:
            d = math.hypot(wx - ego_x, wy - ego_y)
            if d < min_dev:
                min_dev = d
        path_state.path_deviation = min_dev if min_dev < 900.0 else 0.0

        # 3. Obtain Clearance Grid
        clearance_grid = None
        if hasattr(world_model, "safe_space_map") and world_model.safe_space_map is not None:
            clearance_grid = world_model.safe_space_map.clearance_grid
        elif hasattr(world_model, "clearance_grid"):
            clearance_grid = world_model.clearance_grid

        # 4. Evaluate Path Waypoint Safety, Risk, Clearance, and Traversability
        min_clearance = 999.0
        risks = []
        blocked_cnt = 0
        high_risk_cnt = 0
        is_valid = True

        accum_dist = 0.0

        for idx in range(curr_idx, num_pts):
            px, py = world_pts[idx]
            if idx > curr_idx:
                prev_x, prev_y = world_pts[idx - 1]
                accum_dist += math.hypot(px - prev_x, py - prev_y)

            r, c = converter.world_to_grid(px, py)
            cell = grid.get_cell(r, c)

            # Check Hard Traversability Constraint
            if cell is None:
                is_valid = False
                blocked_cnt += 1
            elif not cell.is_drivable and cell.state != CellState.VEHICLE:
                # Cell non-drivable (occupied, pothole, water, etc.)
                is_valid = False
                blocked_cnt += 1
            elif cell.state in (CellState.OUTSIDE_ROAD, CellState.ROAD_BOUNDARY):
                is_valid = False
                blocked_cnt += 1

            # Clearance Sampling
            if clearance_grid is not None and 0 <= r < clearance_grid.shape[0] and 0 <= c < clearance_grid.shape[1]:
                c_val = float(clearance_grid[r, c])
            else:
                c_val = 2.0
            min_clearance = min(min_clearance, c_val)

            # Future Risk Sampling at estimated arrival time
            travel_time = accum_dist / max(1.0, NOMINAL_PLANNING_SPEED)
            if future_risk_field is not None:
                r_val = future_risk_field.get_risk_at_time(travel_time, (px, py), converter)
            else:
                r_val = 0.0
            risks.append(r_val)
            if r_val >= RISK_REPLAN_THRESHOLD:
                high_risk_cnt += 1

        path_state.path_valid = is_valid
        path_state.blocked_cell_count = blocked_cnt
        path_state.high_risk_cell_count = high_risk_cnt
        path_state.minimum_clearance = min_clearance if min_clearance < 900.0 else 0.0

        if risks:
            path_state.current_peak_risk = float(np.max(risks))
            path_state.current_average_risk = float(np.mean(risks))
        else:
            path_state.current_peak_risk = 0.0
            path_state.current_average_risk = 0.0

        # 5. Evaluate Path Degradation
        peak_increase = path_state.current_peak_risk - path_state.original_peak_risk
        is_degraded = (
            not is_valid or
            path_state.current_peak_risk >= RISK_REPLAN_THRESHOLD or
            peak_increase >= PEAK_RISK_INCREASE_THRESHOLD or
            path_state.minimum_clearance < MIN_CLEARANCE_THRESHOLD or
            path_state.path_deviation >= PATH_DEVIATION_THRESHOLD
        )
        path_state.path_degraded = is_degraded

        return path_state
