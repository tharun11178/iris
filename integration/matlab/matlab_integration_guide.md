# MATLAB Automated Driving Toolbox Integration Guide — IRIS Phase 16

## Overview
This guide documents the co-simulation bridge between Python IRIS (`WorldModel`, `SafeSpacePlanner`, `DecisionManager`) and MATLAB / Automated Driving Toolbox / Navigation Toolbox.

---

## Architecture Flow

```text
Python IRIS Simulation Environment
       ↓ (Serialize State to JSON via MatlabAdapter)
iris_matlab_ipc.json / Socket Port 5005
       ↓ (Read & Parse JSON)
MATLAB Automated Driving Toolbox / drivingScenario
       ↓ (Execute MATLAB Trajectory / Vehicle Controller)
Simulink Vehicle Dynamics Blockset
       ↓ (Serialize Control Response)
Python EgoVehicle Control Input ↺
```

---

## Integration Steps

1. **Python Adapter Execution**:
   ```python
   from integration.matlab.matlab_adapter import MatlabAdapter

   adapter = MatlabAdapter(exchange_file="iris_matlab_ipc.json")
   payload = adapter.serialize_iris_state(env, world_model, replanning_manager, decision_result, control_cmd)
   adapter.export_to_file(payload)
   ```

2. **MATLAB Co-Simulation Loop**:
   In MATLAB, instantiate `iris_matlab_interface`:
   ```matlab
   bridge = iris_matlab_interface('iris_matlab_ipc.json');
   stateData = bridge.read_python_state();
   actorPoses = bridge.convert_to_automated_driving_toolbox(stateData);
   controlResp = bridge.compute_matlab_control(stateData);
   bridge.write_matlab_response(controlResp);
   ```

3. **Supported Data Schema**:
   - Ego Vehicle Kinematics (x, y, speed_kmh, heading_rad, steering_angle_deg).
   - Dynamic Traffic Actor Poses (actor_id, actor_type, position, velocity, yaw, behavior_mode).
   - Surface Hazards (hazard_id, hazard_type, position, radius_m, severity).
   - Decision State Machine Signals (`NORMAL_DRIVING`, `CAUTION`, `SLOW_DOWN`, `REPLAN`, `STOP`, `SAFETY_HOLD`).
