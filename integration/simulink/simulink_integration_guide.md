# Simulink Vehicle Dynamics Co-Simulation Guide — IRIS Phase 16

## Overview
This document outlines the signal bus architecture for interfacing IRIS Python decision, risk, and path planner commands with Simulink Vehicle Dynamics Blockset and Powertrain Blockset models.

---

## Bus Architecture

```text
IRIS Python Engine
  ├── EgoVehicleBus (Position, Velocity, Steering, Dimensions)
  ├── TargetTrajectoryBus (20x2 Waypoint Matrix, Target Speed Profile)
  ├── DecisionSafetyBus (State Code, Emergency Stop Flag, Peak Risk, Clearance)
  └── ControlCommandBus (Steering Angle Command, Acceleration Command, Throttle, Brake)
       ↓ (JSON IPC / S-Function / UDP Byte Stream)
Simulink Co-Simulation Block
       ↓
3-DOF / 14-DOF Vehicle Dynamics & Powertrain Model
```

---

## Signal Mapping

| Simulink Bus Element | Type | Units | Description |
|---|---|---|---|
| `EgoVehicleBus.Position` | double[3] | meters | $[X, Y, Z]$ World Coordinates |
| `EgoVehicleBus.Velocity` | double | m/s | Current longitudinal speed |
| `EgoVehicleBus.SteeringAngle` | double | rad | Front wheel steering angle |
| `TargetTrajectoryBus.Waypoints` | double[20][2] | meters | Lookahead waypoint sequence |
| `TargetTrajectoryBus.TargetSpeed` | double | m/s | Decision-modulated target velocity |
| `DecisionSafetyBus.DecisionStateCode` | int32 | Enum | State (0:Normal, 1:Caution, 2:Slow, 3:Replan, 4:Stop, 5:Hold) |
| `DecisionSafetyBus.IsEmergencyStop` | boolean | Flag | Hard emergency override signal |
| `ControlCommandBus.SteeringCommandRad` | double | rad | Pure Pursuit target steering command |
| `ControlCommandBus.AccelerationCommandMs2` | double | m/s² | P-Controller longitudinal acceleration |

---

## Python Setup Code

```python
from integration.simulink.simulink_adapter import SimulinkAdapter

adapter = SimulinkAdapter()
bus_payload = adapter.export_simulink_bus_signals(env, world_model, replanning_manager, decision_result, control_cmd)
adapter.save_bus_data(bus_payload, "simulink_bus_frame.json")
```
