"""
Simulation Environment Engine for IRIS (Phase 1).
Manages simulation state, step dynamics, entities update, and scenario initialization.
"""

from typing import List, Dict, Tuple
from configs.sim_config import ROAD_LENGTH, ROAD_WIDTH
from simulation.entities import (
    Road, EgoVehicle, TrafficActor, SurfaceHazard, ActorType, HazardType, BehaviorMode
)
import math


class SimulationEnvironment:
    """
    Continuous 2D Simulation Environment for IRIS.
    """
    def __init__(self):
        self.road = Road(length=ROAD_LENGTH, width=ROAD_WIDTH)
        self.ego_vehicle = EgoVehicle()
        self.traffic_actors: List[TrafficActor] = []
        self.surface_hazards: List[SurfaceHazard] = []

        self.sim_time: float = 0.0
        self.is_paused: bool = False
        self.is_offroad: bool = False

        # Build initial scenario
        self.reset()

    def reset(self):
        """Reset environment state to initial Phase 1 scenario."""
        self.sim_time = 0.0
        self.is_paused = False
        self.is_offroad = False

        # Initialize Ego Vehicle
        self.ego_vehicle = EgoVehicle(x=5.0, y=0.0, heading=0.0, velocity=8.0)

        # Clear existing entities
        self.surface_hazards.clear()
        self.traffic_actors.clear()

        # -------------------------------------------------------------
        # 1. Populate Unstructured Road Surface Hazards
        # -------------------------------------------------------------
        # Potholes
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=35.0, y=1.5, length=1.8, width=1.2, severity=0.8, uncertainty=0.2)
        )
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=2, hazard_type=HazardType.POTHOLE, x=75.0, y=-2.0, length=2.2, width=1.5, severity=0.9, uncertainty=0.3)
        )
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=3, hazard_type=HazardType.POTHOLE, x=135.0, y=0.5, length=2.0, width=1.4, severity=0.7, uncertainty=0.2)
        )

        # Waterlogged Patch (with high uncertainty for potential hidden pothole)
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=4, hazard_type=HazardType.WATERLOGGED, x=55.0, y=-1.0, length=12.0, width=5.0, severity=0.6, uncertainty=0.85)
        )

        # Raised Surface / Speed Breaker
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=5, hazard_type=HazardType.SPEED_BREAKER, x=95.0, y=0.0, length=1.5, width=11.5, severity=0.5, uncertainty=0.1)
        )

        # Debris on road shoulder
        self.surface_hazards.append(
            SurfaceHazard(hazard_id=6, hazard_type=HazardType.DEBRIS, x=115.0, y=-4.5, length=4.0, width=2.0, severity=0.7, uncertainty=0.3)
        )

        # -------------------------------------------------------------
        # 2. Populate Dynamic Indian Road Traffic Actors
        # -------------------------------------------------------------
        # Auto-rickshaw ahead (swerving around hazards)
        self.traffic_actors.append(
            TrafficActor(actor_id=101, actor_type=ActorType.AUTO_RICKSHAW, x=28.0, y=1.8, heading=0.0, velocity=7.5, behavior=BehaviorMode.SWERVING)
        )

        # Pedestrian crossing unstructured road
        self.traffic_actors.append(
            TrafficActor(actor_id=102, actor_type=ActorType.PEDESTRIAN, x=42.0, y=-5.5, heading=math.pi / 2.0, velocity=1.2, behavior=BehaviorMode.CROSSING)
        )

        # Cattle / Cow on road
        self.traffic_actors.append(
            TrafficActor(actor_id=103, actor_type=ActorType.CATTLE, x=68.0, y=-0.5, heading=0.1, velocity=0.4, behavior=BehaviorMode.SWERVING)
        )

        # Overtaking Motorcycle
        self.traffic_actors.append(
            TrafficActor(actor_id=104, actor_type=ActorType.MOTORCYCLE, x=15.0, y=-2.5, heading=0.0, velocity=13.0, behavior=BehaviorMode.CRUISE)
        )

        # Slow Pushcart on road edge
        self.traffic_actors.append(
            TrafficActor(actor_id=105, actor_type=ActorType.PUSHCART, x=50.0, y=4.5, heading=0.0, velocity=1.5, behavior=BehaviorMode.CRUISE)
        )

        # Opposing Wrong-Side Motorcycle
        self.traffic_actors.append(
            TrafficActor(actor_id=106, actor_type=ActorType.MOTORCYCLE, x=140.0, y=3.2, heading=math.pi, velocity=10.0, behavior=BehaviorMode.WRONG_SIDE)
        )

        # Bus / Truck further ahead
        self.traffic_actors.append(
            TrafficActor(actor_id=107, actor_type=ActorType.BUS_TRUCK, x=120.0, y=-2.0, heading=0.0, velocity=11.0, behavior=BehaviorMode.CRUISE)
        )

    def step(self, dt: float, throttle: float, steering: float):
        """
        Advance simulation by dt seconds.
        :param dt: timestep in seconds
        :param throttle: float [-1.0, 1.0]
        :param steering: float [-1.0, 1.0]
        """
        if self.is_paused:
            return

        # Update Ego Vehicle
        self.ego_vehicle.update(dt, throttle, steering)

        # Check road boundaries
        self.is_offroad = not self.road.is_within_road(self.ego_vehicle.x, self.ego_vehicle.y)

        # Update Dynamic Traffic Actors
        for actor in self.traffic_actors:
            actor.update(dt, self.sim_time)

            # Loop crossers or road end wraparound for smooth continuous simulation
            if actor.behavior == BehaviorMode.CROSSING:
                if actor.y > self.road.y_max + 3.0:
                    actor.y = self.road.y_min - 3.0
            elif actor.x > self.road.length:
                actor.x = 0.0
            elif actor.x < -20.0:
                actor.x = self.road.length

        self.sim_time += dt

    def get_minimum_clearance(self) -> float:
        """Calculate minimum physical clearance distance from ego vehicle to obstacles or road edges."""
        ego = self.ego_vehicle
        min_dist = max(0.0, (self.road.width / 2.0) - abs(ego.y) - (ego.width / 2.0))
        for a in self.traffic_actors:
            d = math.hypot(a.x - ego.x, a.y - ego.y) - (ego.length + a.length) / 2.0
            if d < min_dist:
                min_dist = max(0.0, d)
        return float(min_dist)

    def load_scenario(self, scenario_key: str):
        """
        Loads a reproducible Phase 5 surface hazard scenario (Scenarios A through J).
        """
        self.reset()
        key = str(scenario_key).upper().strip()

        if key in ("A", "NORMAL"):
            self.surface_hazards.clear()

        elif key in ("B", "SINGLE_POTHOLE"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=35.0, y=0.0, length=2.0, width=1.5, severity=0.8, uncertainty=0.1)
            ]

        elif key in ("C", "MULTI_POTHOLE"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.POTHOLE, x=25.0, y=1.2, length=1.8, width=1.2, severity=0.75, uncertainty=0.1),
                SurfaceHazard(hazard_id=2, hazard_type=HazardType.POTHOLE, x=45.0, y=-1.5, length=2.2, width=1.6, severity=0.9, uncertainty=0.2),
                SurfaceHazard(hazard_id=3, hazard_type=HazardType.POTHOLE, x=70.0, y=0.5, length=1.5, width=1.0, severity=0.6, uncertainty=0.1),
            ]

        elif key in ("D", "WATERLOGGED"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.WATERLOGGED, x=45.0, y=0.0, length=14.0, width=6.0, severity=0.65, uncertainty=0.2)
            ]

        elif key in ("E", "HIDDEN_SURFACE_WATER"):
            w_h = SurfaceHazard(hazard_id=1, hazard_type=HazardType.WATERLOGGED, x=45.0, y=0.0, length=12.0, width=5.5, severity=0.7, uncertainty=0.8)
            setattr(w_h, "underlying_surface_known", False)
            self.surface_hazards = [w_h]

        elif key in ("F", "UNEVEN_ROAD"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.DEPRESSION, x=30.0, y=0.0, length=15.0, width=8.0, severity=0.6, uncertainty=0.2)
            ]

        elif key in ("G", "RAISED_SURFACE"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.SPEED_BREAKER, x=40.0, y=0.0, length=1.8, width=11.5, severity=0.5, uncertainty=0.1)
            ]

        elif key in ("H", "DEBRIS"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.DEBRIS, x=35.0, y=-1.0, length=3.5, width=2.5, severity=0.75, uncertainty=0.2)
            ]

        elif key in ("I", "CONSTRUCTION"):
            self.surface_hazards = [
                SurfaceHazard(hazard_id=1, hazard_type=HazardType.DEBRIS, x=50.0, y=1.0, length=12.0, width=6.0, severity=0.85, uncertainty=0.1)
            ]

        elif key in ("J", "COMBINED"):
            # Default rich scenario (already initialized in reset)
            pass

        # -------------------------------------------------------------
        # Phase 6 Mandatory Perception Traffic Scenarios
        # -------------------------------------------------------------
        elif key in ("K", "DENSE_MARKET", "MARKET"):
            self.traffic_actors = [
                TrafficActor(actor_id=201, actor_type=ActorType.PEDESTRIAN, x=20.0, y=1.5, heading=0.0, velocity=0.8, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=202, actor_type=ActorType.PEDESTRIAN, x=25.0, y=-2.0, heading=math.pi / 2.0, velocity=1.0, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=203, actor_type=ActorType.MOTORCYCLE, x=18.0, y=-1.0, heading=0.0, velocity=5.0, behavior=BehaviorMode.SWERVING),
                TrafficActor(actor_id=204, actor_type=ActorType.CAR, x=35.0, y=2.0, heading=0.0, velocity=4.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=205, actor_type=ActorType.BICYCLE, x=15.0, y=4.0, heading=0.0, velocity=3.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=206, actor_type=ActorType.CATTLE, x=30.0, y=-0.5, heading=0.2, velocity=0.3, behavior=BehaviorMode.SWERVING),
                TrafficActor(actor_id=207, actor_type=ActorType.PUSHCART, x=40.0, y=-4.0, heading=0.0, velocity=1.2, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=208, actor_type=ActorType.AUTO_RICKSHAW, x=45.0, y=1.0, heading=0.0, velocity=6.0, behavior=BehaviorMode.SWERVING),
            ]

        elif key in ("L", "INTERSECTION", "UNSIGNALIZED_INTERSECTION"):
            self.traffic_actors = [
                TrafficActor(actor_id=301, actor_type=ActorType.CAR, x=40.0, y=-5.0, heading=math.pi / 2.0, velocity=6.0, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=302, actor_type=ActorType.MOTORCYCLE, x=38.0, y=5.0, heading=-math.pi / 2.0, velocity=8.0, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=303, actor_type=ActorType.PEDESTRIAN, x=42.0, y=-4.5, heading=math.pi / 2.0, velocity=1.2, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=304, actor_type=ActorType.AUTO_RICKSHAW, x=60.0, y=1.0, heading=math.pi, velocity=7.0, behavior=BehaviorMode.CRUISE),
            ]

        elif key in ("M", "CATTLE_CROSSING", "CATTLE"):
            self.traffic_actors = [
                TrafficActor(actor_id=401, actor_type=ActorType.CATTLE, x=30.0, y=-5.0, heading=math.pi / 2.0, velocity=0.6, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=402, actor_type=ActorType.CATTLE, x=35.0, y=4.5, heading=-math.pi / 2.0, velocity=0.4, behavior=BehaviorMode.CROSSING),
                TrafficActor(actor_id=403, actor_type=ActorType.MOTORCYCLE, x=60.0, y=-2.0, heading=0.0, velocity=10.0, behavior=BehaviorMode.CRUISE),
            ]

        elif key in ("N", "HIGHWAY_MERGE", "HIGHWAY"):
            self.traffic_actors = [
                TrafficActor(actor_id=501, actor_type=ActorType.BUS_TRUCK, x=50.0, y=-2.0, heading=0.0, velocity=16.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=502, actor_type=ActorType.CAR, x=25.0, y=2.0, heading=0.0, velocity=20.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=503, actor_type=ActorType.MOTORCYCLE, x=75.0, y=-3.0, heading=0.0, velocity=22.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=504, actor_type=ActorType.CAR, x=90.0, y=1.5, heading=0.0, velocity=18.0, behavior=BehaviorMode.CRUISE),
            ]

        elif key in ("O", "VILLAGE_ROAD", "VILLAGE"):
            self.traffic_actors = [
                TrafficActor(actor_id=601, actor_type=ActorType.PEDESTRIAN, x=25.0, y=3.0, heading=0.0, velocity=1.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=602, actor_type=ActorType.CATTLE, x=45.0, y=0.0, heading=0.0, velocity=0.2, behavior=BehaviorMode.SWERVING),
                TrafficActor(actor_id=603, actor_type=ActorType.BICYCLE, x=15.0, y=-2.0, heading=0.0, velocity=4.0, behavior=BehaviorMode.CRUISE),
                TrafficActor(actor_id=604, actor_type=ActorType.AUTO_RICKSHAW, x=65.0, y=-1.0, heading=math.pi, velocity=8.0, behavior=BehaviorMode.WRONG_SIDE),
            ]

        print(f"[IRIS Sim] Loaded Scenario '{key}': {len(self.traffic_actors)} actors, {len(self.surface_hazards)} hazards active.")

    def toggle_pause(self):
        self.is_paused = not self.is_paused
