"""
IRIS Simulink Signal Bus Co-Simulation Adapter (Combined Phase 16).
Converts IRIS telemetry, path waypoints, future risk, and decision states into Simulink bus signals.
"""

import json
import math
from typing import Dict, List, Tuple, Any, Optional


class SimulinkAdapter:
    """
    Adapter converting IRIS state data to Simulink Vehicle Dynamics Blockset bus structures.
    """

    STATE_ENUM_MAP = {
        "NORMAL_DRIVING": 0,
        "CAUTION": 1,
        "SLOW_DOWN": 2,
        "REPLAN": 3,
        "STOP": 4,
        "SAFETY_HOLD": 5,
        "GOAL_REACHED": 6
    }

    def __init__(self, bus_config_file: str = "integration/simulink/simulink_signals.json"):
        self.bus_config_file = bus_config_file

    def export_simulink_bus_signals(self, env: Any, world_model: Optional[Any] = None,
                                    replanning_manager: Optional[Any] = None,
                                    decision_result: Optional[Any] = None,
                                    control_cmd: Optional[Any] = None) -> Dict[str, Any]:
        """
        Export structured Simulink bus signal hierarchy.
        """
        ego = env.ego_vehicle

        dec_state_str = "NORMAL_DRIVING"
        if decision_result and hasattr(decision_result, "state"):
            dec_state_str = str(decision_result.state.name if hasattr(decision_result.state, "name") else decision_result.state)

        dec_enum_val = self.STATE_ENUM_MAP.get(dec_state_str, 0)
        is_emergency = 1 if dec_state_str in ("STOP", "SAFETY_HOLD") else 0

        # Sample path waypoints (up to 20 points)
        waypoints = []
        if ego.current_path and len(ego.current_path) > 0:
            for px, py in ego.current_path[:20]:
                waypoints.append([float(px), float(py)])
        while len(waypoints) < 20:
            waypoints.append([float(ego.x), float(ego.y)])

        peak_risk = 0.0
        if replanning_manager and hasattr(replanning_manager, "current_state") and replanning_manager.current_state:
            peak_risk = float(replanning_manager.current_state.current_peak_risk)

        target_speed_ms = float(control_cmd.target_speed) if control_cmd else float(ego.target_speed)
        steer_rad = float(control_cmd.steering_command) if control_cmd else float(ego.steering_angle)
        accel_ms2 = float(control_cmd.acceleration) if control_cmd else 0.0

        bus_payload = {
            "SimTime": float(env.sim_time),
            "EgoVehicleBus": {
                "Position": [float(ego.x), float(ego.y), 0.0],
                "Velocity": float(ego.velocity),
                "Heading": float(ego.heading),
                "SteeringAngle": float(ego.steering_angle),
                "Length": float(ego.length),
                "Width": float(ego.width)
            },
            "TargetTrajectoryBus": {
                "Waypoints": waypoints,
                "NumWaypoints": len(waypoints),
                "TargetSpeed": target_speed_ms
            },
            "DecisionSafetyBus": {
                "DecisionStateCode": dec_enum_val,
                "IsEmergencyStop": is_emergency,
                "PeakFutureRisk": peak_risk,
                "MinimumClearance": float(env.get_minimum_clearance())
            },
            "ControlCommandBus": {
                "SteeringCommandRad": steer_rad,
                "AccelerationCommandMs2": accel_ms2,
                "Throttle": float(control_cmd.throttle_command) if control_cmd else 0.0,
                "Brake": float(control_cmd.brake_command) if control_cmd else 0.0
            }
        }
        return bus_payload

    def save_bus_data(self, bus_payload: Dict[str, Any], filepath: str = "simulink_bus_frame.json") -> str:
        """Save bus payload to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(bus_payload, f, indent=2)
        return filepath
