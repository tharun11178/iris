"""
IRIS Vehicle Controller Facade (Combined Phase 13).
Orchestrates DecisionManager, SpeedController, SteeringController, LongitudinalController,
and outputs unified ControlCommand to drive the EgoVehicle in closed-loop simulation.
"""

import math
from dataclasses import dataclass
from typing import Tuple, Optional, Any
from world.world_model import WorldModel
from future_risk.future_risk_field import FutureRiskField
from replanning.replanning_manager import ReplanningManager
from planning.path import Path
from decision.decision_state import DecisionState, DecisionResult
from decision.decision_manager import DecisionManager
from control.speed_controller import SpeedController
from control.steering_controller import SteeringController
from control.longitudinal_controller import LongitudinalController
from control.config import MAX_STEERING_ANGLE, MAX_SPEED


@dataclass
class ControlCommand:
    """
    Unified control command returned by VehicleController.
    """
    steering_angle: float            # Steering angle in radians
    steering_command: float          # Normalized steering input [-1.0, 1.0]
    acceleration: float            # Longitudinal acceleration in m/s²
    throttle_command: float          # Normalized throttle/brake input [-1.0, 1.0]
    target_speed: float              # Target speed in m/s
    target_speed_kmh: float          # Target speed in km/h
    current_speed_kmh: float         # Current speed in km/h
    lookahead_point: Tuple[float, float] # (x, y) target lookahead point in world meters
    decision_result: DecisionResult  # Active high-level decision outcome
    braking_state: str               # "NORMAL", "HARD_BRAKING", "EMERGENCY_STOP", "STOPPED", etc.
    controller_type: str = "PURE_PURSUIT"


class VehicleController:
    """
    Central controller facade executing closed-loop autonomous driving control.
    """

    def __init__(self):
        self.decision_manager = DecisionManager()
        self.speed_controller = SpeedController()
        self.steering_controller = SteeringController()
        self.longitudinal_controller = LongitudinalController()
        self.last_command: Optional[ControlCommand] = None

    def compute_control(
        self,
        world_model: WorldModel,
        future_risk_field: Optional[FutureRiskField] = None,
        replanning_manager: Optional[ReplanningManager] = None,
        dt: float = 0.05,
        current_time: float = 0.0,
        goal_pos: Optional[Tuple[float, float]] = None,
    ) -> ControlCommand:
        """
        Executes full decision & control pipeline and returns actionable ControlCommand.
        """
        converter = world_model.converter
        ego = world_model.ego_state
        def_start = converter.sim_to_world(5.0, 0.0)
        ego_pos = (ego.get("x", def_start[0]), ego.get("y", def_start[1]))
        ego_heading = ego.get("heading", 0.0)
        current_speed = ego.get("velocity", 0.0)

        # 1. Evaluate Decision State & Safety Priority
        decision_res = self.decision_manager.evaluate_decision(
            world_model=world_model,
            future_risk_field=future_risk_field,
            replanning_manager=replanning_manager,
            current_time=current_time,
            goal_pos=goal_pos,
        )

        # Extract path metrics for speed controller
        path_state = replanning_manager.current_state if replanning_manager else None
        active_path: Optional[Path] = path_state.path if path_state else None
        min_clearance = path_state.minimum_clearance if path_state else 999.0
        peak_risk = path_state.current_peak_risk if path_state else 0.0

        if active_path is None and hasattr(world_model, "planning_result") and world_model.planning_result:
            active_path = world_model.planning_result.selected_path

        # 2. Compute Target Speed
        target_speed = self.speed_controller.compute_target_speed(
            current_speed=current_speed,
            decision_state=decision_res.state,
            future_risk=peak_risk,
            minimum_clearance=min_clearance,
            target_speed_factor=decision_res.target_speed_factor,
        )

        # 3. Compute Pure Pursuit Steering Angle & Lookahead Point
        steering_angle, lookahead_pt = self.steering_controller.compute_steering(
            vehicle_position=ego_pos,
            vehicle_heading=ego_heading,
            current_speed=current_speed,
            current_path=active_path,
        )
        norm_steering = float(steering_angle / MAX_STEERING_ANGLE) if MAX_STEERING_ANGLE > 0 else 0.0
        norm_steering = max(-1.0, min(1.0, norm_steering))

        # 4. Compute Longitudinal Acceleration & Throttle Command
        is_emergency = (decision_res.state in (DecisionState.STOP, DecisionState.SAFETY_HOLD))
        accel, throttle, braking_state = self.longitudinal_controller.compute_longitudinal_control(
            current_speed=current_speed,
            target_speed=target_speed,
            dt=dt,
            is_emergency=is_emergency,
        )

        cmd = ControlCommand(
            steering_angle=steering_angle,
            steering_command=norm_steering,
            acceleration=accel,
            throttle_command=throttle,
            target_speed=target_speed,
            target_speed_kmh=target_speed * 3.6,
            current_speed_kmh=current_speed * 3.6,
            lookahead_point=lookahead_pt,
            decision_result=decision_res,
            braking_state=braking_state,
            controller_type="PURE_PURSUIT",
        )
        self.last_command = cmd
        return cmd
