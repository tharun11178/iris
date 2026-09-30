"""
IRIS MATLAB Interoperability Adapter (Combined Phase 16).
Provides serialized JSON state exchange and TCP socket bridge for MATLAB Automated Driving Toolbox co-simulation.
"""

import os
import json
import socket
import math
from typing import Dict, Any, Optional, List


class MatlabAdapter:
    """
    Adapter bridging Python IRIS WorldModel and Control System with MATLAB environment.
    Supports file IPC and TCP socket streaming.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 5005, exchange_file: str = "iris_matlab_ipc.json"):
        self.host = host
        self.port = port
        self.exchange_file = exchange_file

    def serialize_iris_state(self, env: Any, world_model: Optional[Any] = None,
                             replanning_manager: Optional[Any] = None,
                             decision_result: Optional[Any] = None,
                             control_cmd: Optional[Any] = None) -> Dict[str, Any]:
        """
        Serialize complete IRIS runtime state to MATLAB-compatible JSON schema.
        """
        ego = env.ego_vehicle

        actors_list = []
        for actor in env.traffic_actors:
            act_type = str(actor.actor_type.name if hasattr(actor.actor_type, "name") else actor.actor_type)
            actors_list.append({
                "actor_id": int(actor.actor_id),
                "actor_type": act_type,
                "position": [float(actor.x), float(actor.y)],
                "velocity": [float(actor.vx if hasattr(actor, "vx") else actor.velocity * math.cos(actor.heading)),
                             float(actor.vy if hasattr(actor, "vy") else actor.velocity * math.sin(actor.heading))],
                "heading_rad": float(actor.heading),
                "length_m": float(actor.length),
                "width_m": float(actor.width),
                "behavior_mode": str(actor.behavior.name if hasattr(actor.behavior, "name") else actor.behavior)
            })

        hazards_list = []
        for hazard in env.surface_hazards:
            hz_type = str(hazard.hazard_type.name if hasattr(hazard.hazard_type, "name") else hazard.hazard_type)
            hz_id = getattr(hazard, "hazard_id", 1)
            try:
                hz_id = int(hz_id)
            except Exception:
                hz_id = 1
            hz_x = getattr(hazard, "x", hazard.position[0] if hasattr(hazard, "position") else 0.0)
            hz_y = getattr(hazard, "y", hazard.position[1] if hasattr(hazard, "position") else 0.0)
            hz_rad = getattr(hazard, "radius", max(getattr(hazard, "length", 1.0), getattr(hazard, "width", 1.0)) / 2.0)
            hz_sev = getattr(hazard, "severity", 0.5)
            hazards_list.append({
                "hazard_id": hz_id,
                "hazard_type": hz_type,
                "position": [float(hz_x), float(hz_y)],
                "radius_m": float(hz_rad),
                "severity": float(hz_sev)
            })

        peak_risk = 0.0
        if replanning_manager and hasattr(replanning_manager, "current_state") and replanning_manager.current_state:
            peak_risk = float(replanning_manager.current_state.current_peak_risk)

        dec_state = "NORMAL_DRIVING"
        if decision_result and hasattr(decision_result, "state"):
            dec_state = str(decision_result.state.name if hasattr(decision_result.state, "name") else decision_result.state)

        target_speed_ms = float(control_cmd.target_speed) if control_cmd else float(ego.target_speed)
        steering_rad = float(control_cmd.steering_command) if control_cmd else float(ego.steering_angle)
        accel_ms2 = float(control_cmd.acceleration) if control_cmd else 0.0

        payload = {
            "timestamp_s": float(env.sim_time),
            "ego_vehicle": {
                "position": [float(ego.x), float(ego.y)],
                "velocity_ms": float(ego.velocity),
                "speed_kmh": float(ego.velocity * 3.6),
                "heading_rad": float(ego.heading),
                "steering_angle_deg": float(math.degrees(ego.steering_angle)),
                "length_m": float(ego.length),
                "width_m": float(ego.width),
                "decision_state": dec_state,
                "target_speed_ms": target_speed_ms,
                "steering_command_rad": steering_rad,
                "acceleration_command_ms2": accel_ms2
            },
            "road": {
                "width_m": float(env.road.width),
                "length_m": float(env.road.length)
            },
            "traffic_actors": actors_list,
            "surface_hazards": hazards_list,
            "metrics": {
                "minimum_clearance_m": float(env.get_minimum_clearance()),
                "peak_future_risk": peak_risk,
                "replanning_count": int(replanning_manager.metrics.total_replans if replanning_manager else 0)
            }
        }
        return payload

    def export_to_file(self, state_dict: Dict[str, Any], filepath: Optional[str] = None) -> str:
        """Export serialized state to JSON file for MATLAB file IPC."""
        target_path = filepath if filepath else self.exchange_file
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
        return target_path

    def import_from_file(self, filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Import MATLAB response payload from JSON file."""
        target_path = filepath if filepath else self.exchange_file
        if not os.path.exists(target_path):
            return None
        with open(target_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def parse_matlab_control_response(self, response_dict: Dict[str, Any]) -> Dict[str, float]:
        """
        Parse MATLAB Vehicle Dynamics control output payload.
        Expects keys: steering_angle_deg, target_speed_kmh, throttle, brake.
        """
        steer_deg = float(response_dict.get("steering_angle_deg", 0.0))
        speed_kmh = float(response_dict.get("target_speed_kmh", 20.0))
        throttle = float(response_dict.get("throttle", 0.0))
        brake = float(response_dict.get("brake", 0.0))

        return {
            "steering_angle_rad": math.radians(steer_deg),
            "target_speed_ms": speed_kmh / 3.6,
            "throttle_cmd": throttle,
            "brake_cmd": brake
        }
