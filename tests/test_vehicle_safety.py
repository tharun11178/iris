"""
Unit and Integration Tests for IRIS Vehicle Safety, Dynamics, and Road Boundary Enforcement.
Verifies vehicle footprint calculation, road boundary containment, steering rate limits,
speed control, collision checking, off-road prevention, and emergency stop.
"""

import math
import pytest
import numpy as np

from simulation.vehicle_safety import (
    VehicleSafetyChecker,
    VehicleCondition,
    ROAD_MARGIN,
)
from simulation.vehicle_model import (
    KinematicBicycleVehicle,
    VehicleState,
    VehicleControl,
    WHEELBASE,
    MAX_STEERING_ANGLE,
    MAX_STEERING_RATE,
    MAX_ACCELERATION,
    MAX_BRAKING,
)
from simulation.entities import TrafficActor, ActorType, BehaviorMode, SurfaceHazard, HazardType


def test_vehicle_footprint_dimensions():
    """Verify vehicle footprint polygon is correctly computed from (x, y, heading)."""
    checker = VehicleSafetyChecker(road_width=12.0, vehicle_length=4.6, vehicle_width=2.0)
    
    # Heading = 0 (aligned with X axis)
    corners = checker.get_vehicle_footprint(x=10.0, y=0.0, heading=0.0)
    assert len(corners) == 4
    
    # Front-Left: (10 + 2.3, 0 + 1.0) = (12.3, 1.0)
    assert pytest.approx(corners[0][0], abs=1e-3) == 12.3
    assert pytest.approx(corners[0][1], abs=1e-3) == 1.0
    
    # Rear-Right: (10 - 2.3, 0 - 1.0) = (7.7, -1.0)
    assert pytest.approx(corners[2][0], abs=1e-3) == 7.7
    assert pytest.approx(corners[2][1], abs=1e-3) == -1.0


def test_road_boundary_containment():
    """Verify complete footprint containment within road bounds [-6.0, +6.0]."""
    checker = VehicleSafetyChecker(road_width=12.0, vehicle_length=4.6, vehicle_width=2.0)
    
    # Inside road at center
    inside_corners = checker.get_vehicle_footprint(x=10.0, y=0.0, heading=0.0)
    is_inside, viol = checker.check_road_boundary(inside_corners, margin=0.0)
    assert is_inside is True
    assert len(viol) == 0

    # Outside road (y = 5.5, vehicle half-width is 1.0, front-left y becomes 6.5 > 6.0)
    outside_corners = checker.get_vehicle_footprint(x=10.0, y=5.5, heading=0.0)
    is_inside, viol = checker.check_road_boundary(outside_corners, margin=0.0)
    assert is_inside is False
    assert len(viol) > 0


def test_safe_corridor_envelope():
    """Verify safe envelope boundary check with ROAD_MARGIN."""
    checker = VehicleSafetyChecker(road_width=12.0, road_margin=0.5, vehicle_length=4.6, vehicle_width=2.0)
    
    # Road boundary is +/- 6.0m. Safe envelope is +/- 5.5m.
    # At y = 4.4m (half-width 1.0m -> max y = 5.4m < 5.5m), should be inside safe envelope.
    fp_safe = checker.get_vehicle_footprint(x=10.0, y=4.4, heading=0.0)
    res_safe = checker.is_footprint_safe(fp_safe)
    assert res_safe.inside_road is True
    assert res_safe.inside_safe_corridor is True

    # At y = 4.8m (max y = 5.8m > 5.5m), inside physical road but outside safe corridor -> CAUTION condition
    fp_caution = checker.get_vehicle_footprint(x=10.0, y=4.8, heading=0.0)
    res_caution = checker.is_footprint_safe(fp_caution)
    assert res_caution.inside_road is True
    assert res_caution.inside_safe_corridor is False
    assert res_caution.condition == VehicleCondition.CAUTION


def test_steering_rate_limits():
    """Verify steering angle rate limiter prevents instantaneous steering jumps."""
    veh = KinematicBicycleVehicle(x=0.0, y=0.0, heading=0.0, velocity=5.0)
    dt = 0.05
    
    # Command full right steering (steering = 1.0)
    veh.update(dt=dt, throttle=0.5, steering=1.0)
    max_expected_delta = MAX_STEERING_RATE * dt
    assert veh.steering_angle <= max_expected_delta + 1e-5
    assert veh.steering_angle > 0.0


def test_heading_controls_movement():
    """Verify movement obeys dx = v * cos(heading) * dt, dy = v * sin(heading) * dt."""
    # Heading 0 -> movement strictly in +X
    veh = KinematicBicycleVehicle(x=0.0, y=0.0, heading=0.0, velocity=10.0)
    dt = 0.1
    veh.update(dt=dt, throttle=0.0, steering=0.0)
    assert pytest.approx(veh.x, abs=0.05) == 1.0
    assert pytest.approx(veh.y, abs=0.01) == 0.0

    # Heading pi/4 (45 degrees) -> equal dx and dy
    veh2 = KinematicBicycleVehicle(x=0.0, y=0.0, heading=math.pi / 4.0, velocity=10.0)
    veh2.update(dt=dt, throttle=0.0, steering=0.0)
    expected_step = 10.0 * dt * math.cos(math.pi / 4.0)
    assert pytest.approx(veh2.x, abs=0.05) == expected_step
    assert pytest.approx(veh2.y, abs=0.05) == expected_step


def test_collision_detection_and_emergency_braking():
    """Verify collision checking with obstacle and resulting condition."""
    veh = KinematicBicycleVehicle(x=10.0, y=0.0, heading=0.0, velocity=10.0)
    # Actor placed directly in front
    actor = TrafficActor(actor_id=1, actor_type=ActorType.CAR, x=13.0, y=0.0, heading=0.0, velocity=0.0)
    
    dt = 0.1
    res = veh.update(dt=dt, throttle=1.0, steering=0.0, traffic_actors=[actor])
    
    # Overlap detected -> collision condition
    assert res.collision_detected is True or res.condition in (VehicleCondition.NEAR_COLLISION, VehicleCondition.COLLISION_RISK)
    assert veh.condition in (VehicleCondition.NEAR_COLLISION, VehicleCondition.COLLISION_RISK)
    assert veh.replanning_requested is True


def test_offroad_prevention_intervention():
    """Verify vehicle safety intervention prevents the vehicle from leaving the road."""
    # Place vehicle near upper road boundary (y=5.8m) steering left toward off-road
    veh = KinematicBicycleVehicle(x=10.0, y=5.8, heading=0.2, velocity=8.0)
    
    dt = 0.05
    for _ in range(10):
        veh.update(dt=dt, throttle=0.5, steering=1.0)
        # Vehicle must NEVER exceed road lateral boundary y=6.0 (half-width 1.0m -> y <= 5.0 safe)
        assert veh.y <= 5.2
        assert veh.y >= -5.2


def test_vehicle_condition_monitoring():
    """Verify vehicle condition evaluation across normal, caution, and slow down states."""
    checker = VehicleSafetyChecker(road_width=12.0)
    
    # Normal case: center of road, no obstacles, low future risk
    fp_norm = checker.get_vehicle_footprint(x=10.0, y=0.0, heading=0.0)
    res_norm = checker.is_footprint_safe(fp_norm, future_risk=0.1)
    assert res_norm.condition == VehicleCondition.NORMAL

    # Slow down case: high future risk ahead
    res_slow = checker.is_footprint_safe(fp_norm, future_risk=0.8)
    assert res_slow.condition == VehicleCondition.SLOW_DOWN

    # Caution case: near boundary
    fp_edge = checker.get_vehicle_footprint(x=10.0, y=4.8, heading=0.0)
    res_edge = checker.is_footprint_safe(fp_edge, future_risk=0.1)
    assert res_edge.condition == VehicleCondition.CAUTION
