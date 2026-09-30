"""
IRIS Vehicle Module — Unified Vehicle Interface.
Exposes KinematicBicycleVehicle, EgoVehicle, VehicleState, VehicleControl,
VehicleSafetyChecker, and VehicleCondition.
"""

from simulation.vehicle_safety import (
    VehicleSafetyChecker,
    VehicleCondition,
    FootprintCheckResult,
    ROAD_MARGIN,
)
from simulation.vehicle_model import (
    KinematicBicycleVehicle,
    VehicleState,
    VehicleControl,
    WHEELBASE,
    VEHICLE_LENGTH,
    VEHICLE_WIDTH,
    MAX_STEERING_ANGLE,
    MAX_STEERING_RATE,
    MAX_ACCELERATION,
    MAX_BRAKING,
    MAX_SPEED,
    MIN_SPEED,
)

# Alias EgoVehicle to KinematicBicycleVehicle
EgoVehicle = KinematicBicycleVehicle

__all__ = [
    "EgoVehicle",
    "KinematicBicycleVehicle",
    "VehicleState",
    "VehicleControl",
    "VehicleSafetyChecker",
    "VehicleCondition",
    "FootprintCheckResult",
    "ROAD_MARGIN",
    "WHEELBASE",
    "VEHICLE_LENGTH",
    "VEHICLE_WIDTH",
    "MAX_STEERING_ANGLE",
    "MAX_STEERING_RATE",
    "MAX_ACCELERATION",
    "MAX_BRAKING",
    "MAX_SPEED",
    "MIN_SPEED",
]
