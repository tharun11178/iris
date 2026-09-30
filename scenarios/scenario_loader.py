"""
IRIS Scenario Registry & Loader (Combined Phase 14).
Provides reproducible, config-driven definitions for 5 mandatory Indian road scenarios,
8 road surface scenarios, and 11 advanced stress test scenarios.
"""

import random
import math
import numpy as np
from typing import Dict, List, Optional
from simulation.entities import ActorType, HazardType, BehaviorMode
from scenarios.scenario_definition import (
    RoadType,
    DifficultyLevel,
    ScenarioActor,
    ScenarioHazard,
    ScenarioEvent,
    ScenarioEventType,
    ExpectedEvent,
    ScenarioDefinition,
)


class ScenarioRegistry:
    """
    Central repository of predefined IRIS scenarios.
    """

    def __init__(self):
        self._scenarios: Dict[str, ScenarioDefinition] = {}
        self._populate_all_scenarios()

    def get_scenario(self, scenario_id: str, seed: int = 42) -> Optional[ScenarioDefinition]:
        """Returns instantiated ScenarioDefinition with configured random seed."""
        key = scenario_id.upper().strip()
        # Aliases mapping
        alias_map = {
            "CATTLE_CROSSING": "SUDDEN_CATTLE_CROSSING",
            "VILLAGE_ROAD": "UNMARKED_VILLAGE_ROAD",
            "INTERSECTION": "UNSIGNALIZED_URBAN_INTERSECTION",
            "MARKET": "DENSE_MARKET",
            "HIGHWAY": "HIGHWAY_MERGE",
        }
        if key in alias_map:
            key = alias_map[key]

        if key in self._scenarios:
            sc = self._scenarios[key]
            sc.seed = seed
            return sc
        return None

    def list_scenarios(self) -> List[str]:
        return list(self._scenarios.keys())

    def _populate_all_scenarios(self):
        # -------------------------------------------------------------
        # 1. FIVE MANDATORY INDIAN ROAD SCENARIOS
        # -------------------------------------------------------------
        self._scenarios["UNMARKED_VILLAGE_ROAD"] = ScenarioDefinition(
            scenario_id="UNMARKED_VILLAGE_ROAD",
            name="Unmarked Village Road",
            description="Narrow unpaved village road with no markings, pedestrians, motorcycles, roaming cattle, and severe potholes.",
            road_type=RoadType.VILLAGE_ROAD,
            difficulty=DifficultyLevel.HARD,
            duration=30.0,
            start_pos=(5.0, 0.0),
            goal_pos=(140.0, 0.0),
            actors=[
                ScenarioActor(101, ActorType.PEDESTRIAN, 25.0, 2.2, heading=-1.57, velocity=1.2, behavior=BehaviorMode.CROSSING),
                ScenarioActor(102, ActorType.MOTORCYCLE, 45.0, -1.8, heading=3.14, velocity=6.0, behavior=BehaviorMode.WRONG_SIDE),
                ScenarioActor(103, ActorType.CATTLE, 70.0, 0.5, heading=0.0, velocity=0.5, behavior=BehaviorMode.CRUISE),
                ScenarioActor(104, ActorType.BICYCLE, 110.0, 2.0, heading=0.0, velocity=3.0, behavior=BehaviorMode.CRUISE),
            ],
            hazards=[
                ScenarioHazard(1, HazardType.POTHOLE, 35.0, 0.5, length=2.0, width=1.5, severity=0.85, uncertainty=0.2),
                ScenarioHazard(2, HazardType.POTHOLE, 80.0, -1.2, length=2.5, width=1.8, severity=0.90, uncertainty=0.3),
                ScenarioHazard(3, HazardType.WATERLOGGED, 100.0, 0.0, length=8.0, width=4.5, severity=0.60, uncertainty=0.7),
            ],
            events=[
                ScenarioEvent(5.0, ScenarioEventType.ENTER_ROAD, {"actor_id": 105, "actor_type": ActorType.CATTLE, "x": 55.0, "y": -4.0}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Cattle crossing in village channel", "cattle_crossing", "Slow down and execute safe-space detour"),
                ExpectedEvent("EVT_02", "Pothole avoidance", "risk_increase", "Adjust trajectory around severe pothole"),
            ]
        )

        self._scenarios["UNSIGNALIZED_URBAN_INTERSECTION"] = ScenarioDefinition(
            scenario_id="UNSIGNALIZED_URBAN_INTERSECTION",
            name="Unsignalized Urban Intersection",
            description="Uncontrolled 4-way intersection with chaotic crossing traffic, auto-rickshaws, pedestrians, and no traffic signal.",
            road_type=RoadType.URBAN_INTERSECTION,
            difficulty=DifficultyLevel.HARD,
            duration=30.0,
            start_pos=(5.0, 0.0),
            goal_pos=(140.0, 0.0),
            actors=[
                ScenarioActor(201, ActorType.AUTO_RICKSHAW, 60.0, 4.0, heading=-1.57, velocity=4.5, behavior=BehaviorMode.CROSSING),
                ScenarioActor(202, ActorType.CAR, 62.0, -4.5, heading=1.57, velocity=5.0, behavior=BehaviorMode.CROSSING),
                ScenarioActor(203, ActorType.PEDESTRIAN, 58.0, 2.5, heading=-1.57, velocity=1.1, behavior=BehaviorMode.CROSSING),
                ScenarioActor(204, ActorType.MOTORCYCLE, 85.0, 1.5, heading=3.14, velocity=7.0, behavior=BehaviorMode.SWERVING),
            ],
            hazards=[
                ScenarioHazard(10, HazardType.SPEED_BREAKER, 50.0, 0.0, length=1.5, width=12.0, severity=0.5, uncertainty=0.1),
            ],
            events=[
                ScenarioEvent(3.0, ScenarioEventType.SPAWN_OBJECT, {"actor_id": 205, "actor_type": ActorType.MOTORCYCLE, "x": 65.0, "y": -3.5, "heading": 1.57, "velocity": 6.5}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Intersection crossing conflict", "risk_increase", "Yield and select safe gap channel"),
            ]
        )

        self._scenarios["HIGHWAY_MERGE"] = ScenarioDefinition(
            scenario_id="HIGHWAY_MERGE",
            name="Highway Merge",
            description="Multi-lane highway segment with slow heavy truck, fast passing cars, and merging motorcycle with changing gaps.",
            road_type=RoadType.HIGHWAY,
            difficulty=DifficultyLevel.MODERATE,
            duration=30.0,
            start_pos=(5.0, 0.0),
            goal_pos=(140.0, 0.0),
            actors=[
                ScenarioActor(301, ActorType.BUS_TRUCK, 40.0, 1.8, heading=0.0, velocity=5.0, behavior=BehaviorMode.CRUISE),
                ScenarioActor(302, ActorType.CAR, 25.0, -1.8, heading=0.0, velocity=10.0, behavior=BehaviorMode.CRUISE),
                ScenarioActor(303, ActorType.MOTORCYCLE, 55.0, -4.0, heading=0.5, velocity=7.0, behavior=BehaviorMode.SWERVING),
            ],
            hazards=[],
            events=[
                ScenarioEvent(4.0, ScenarioEventType.CHANGE_DIRECTION, {"actor_id": 303, "heading": 0.0, "behavior": BehaviorMode.CRUISE}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Highway truck gap evaluation", "path_change", "Overtake slow truck in adjacent safe corridor"),
            ]
        )

        self._scenarios["DENSE_MARKET"] = ScenarioDefinition(
            scenario_id="DENSE_MARKET",
            name="Dense Market",
            description="Ultra-crowded market street with pushcarts, bicycles, wandering cattle, pedestrians, and narrow drivable corridors.",
            road_type=RoadType.MARKET_ROAD,
            difficulty=DifficultyLevel.EXTREME,
            duration=30.0,
            start_pos=(5.0, 0.0),
            goal_pos=(140.0, 0.0),
            actors=[
                ScenarioActor(401, ActorType.PUSHCART, 30.0, 1.2, heading=0.0, velocity=1.0, behavior=BehaviorMode.CRUISE),
                ScenarioActor(402, ActorType.PEDESTRIAN, 35.0, -1.5, heading=0.0, velocity=1.2, behavior=BehaviorMode.CRUISE),
                ScenarioActor(403, ActorType.BICYCLE, 50.0, 1.8, heading=0.0, velocity=2.5, behavior=BehaviorMode.CRUISE),
                ScenarioActor(404, ActorType.CATTLE, 75.0, -0.5, heading=0.0, velocity=0.4, behavior=BehaviorMode.CRUISE),
                ScenarioActor(405, ActorType.MOTORCYCLE, 90.0, -1.8, heading=3.14, velocity=4.0, behavior=BehaviorMode.WRONG_SIDE),
            ],
            hazards=[
                ScenarioHazard(20, HazardType.DEBRIS, 45.0, -2.5, length=3.0, width=1.8, severity=0.6, uncertainty=0.2),
            ],
            events=[
                ScenarioEvent(6.0, ScenarioEventType.CHANGE_DIRECTION, {"actor_id": 402, "heading": 1.57, "behavior": BehaviorMode.CROSSING}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Market crowd congestion", "slowdown", "Reduce speed and navigate narrow negative space"),
            ]
        )

        self._scenarios["SUDDEN_CATTLE_CROSSING"] = ScenarioDefinition(
            scenario_id="SUDDEN_CATTLE_CROSSING",
            name="Sudden Cattle Crossing",
            description="Initially open road where cattle suddenly enters the travel corridor, triggering predicted collision and immediate replanning.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            duration=30.0,
            start_pos=(5.0, 0.0),
            goal_pos=(140.0, 0.0),
            actors=[
                ScenarioActor(501, ActorType.CAR, 80.0, 2.0, heading=0.0, velocity=7.0, behavior=BehaviorMode.CRUISE),
            ],
            hazards=[],
            events=[
                ScenarioEvent(2.5, ScenarioEventType.ENTER_ROAD, {"actor_id": 502, "actor_type": ActorType.CATTLE, "x": 42.0, "y": -5.0, "heading": 1.57, "velocity": 2.0}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Sudden cattle entry", "cattle_crossing", "Detect sudden obstacle and trigger emergency replan"),
                ExpectedEvent("EVT_02", "Adaptive Replanning", "replanning", "Execute smooth path transition into safe corridor"),
            ]
        )

        # -------------------------------------------------------------
        # 2. ROAD SURFACE SCENARIOS
        # -------------------------------------------------------------
        self._scenarios["POTHOLE_AVOIDANCE"] = ScenarioDefinition(
            scenario_id="POTHOLE_AVOIDANCE",
            name="Pothole Avoidance",
            description="Cluster of deep severe potholes requiring safe-space corridor detour.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.MODERATE,
            hazards=[
                ScenarioHazard(301, HazardType.POTHOLE, 35.0, 0.0, length=2.2, width=1.6, severity=0.9, uncertainty=0.1),
                ScenarioHazard(302, HazardType.POTHOLE, 60.0, 1.2, length=2.5, width=1.5, severity=0.85, uncertainty=0.2),
            ]
        )

        self._scenarios["WATERLOGGING"] = ScenarioDefinition(
            scenario_id="WATERLOGGING",
            name="Monsoon Waterlogging",
            description="Extended waterlogged road patch requiring reduced target speed.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.MODERATE,
            hazards=[
                ScenarioHazard(303, HazardType.WATERLOGGED, 50.0, 0.0, length=15.0, width=6.0, severity=0.6, uncertainty=0.5),
            ]
        )

        self._scenarios["DEEP_WATER"] = ScenarioDefinition(
            scenario_id="DEEP_WATER",
            name="Deep Water Inundation",
            description="Deep non-traversable flooded road segment requiring full corridor deviation.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            hazards=[
                ScenarioHazard(304, HazardType.WATERLOGGED, 55.0, 0.0, length=12.0, width=8.0, severity=0.95, uncertainty=0.9),
            ]
        )

        self._scenarios["UNEVEN_TERRAIN"] = ScenarioDefinition(
            scenario_id="UNEVEN_TERRAIN",
            name="Uneven Terrain",
            description="Continuous low-traversability unpaved road segment.",
            road_type=RoadType.VILLAGE_ROAD,
            difficulty=DifficultyLevel.MODERATE,
            hazards=[
                ScenarioHazard(305, HazardType.ROAD_DEPRESSION, 40.0, 0.0, length=20.0, width=6.0, severity=0.5, uncertainty=0.2),
            ]
        )

        self._scenarios["RAISED_SPEED_BREAKER"] = ScenarioDefinition(
            scenario_id="RAISED_SPEED_BREAKER",
            name="Raised Speed Breaker",
            description="Full-width unmarked Indian speed breaker requiring deceleration.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.EASY,
            hazards=[
                ScenarioHazard(306, HazardType.SPEED_BREAKER, 50.0, 0.0, length=1.8, width=12.0, severity=0.5, uncertainty=0.1),
            ]
        )

        self._scenarios["DEBRIS"] = ScenarioDefinition(
            scenario_id="DEBRIS",
            name="Roadside Debris",
            description="Construction debris spilled on road shoulder.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.EASY,
            hazards=[
                ScenarioHazard(307, HazardType.DEBRIS, 45.0, -2.0, length=5.0, width=2.5, severity=0.7, uncertainty=0.2),
            ]
        )

        self._scenarios["CONSTRUCTION"] = ScenarioDefinition(
            scenario_id="CONSTRUCTION",
            name="Road Work Construction Zone",
            description="Lane closure due to active road construction work.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            hazards=[
                ScenarioHazard(308, HazardType.DEBRIS, 60.0, 1.5, length=15.0, width=3.5, severity=0.95, uncertainty=0.1),
            ]
        )

        self._scenarios["COMBINED_SURFACE_HAZARDS"] = ScenarioDefinition(
            scenario_id="COMBINED_SURFACE_HAZARDS",
            name="Combined Surface Hazards",
            description="Complex multi-hazard surface with potholes, waterlogging, and speed breakers.",
            road_type=RoadType.VILLAGE_ROAD,
            difficulty=DifficultyLevel.EXTREME,
            hazards=[
                ScenarioHazard(309, HazardType.POTHOLE, 35.0, 1.2, length=2.0, width=1.5, severity=0.8, uncertainty=0.2),
                ScenarioHazard(310, HazardType.WATERLOGGED, 60.0, -1.0, length=10.0, width=5.0, severity=0.7, uncertainty=0.8),
                ScenarioHazard(311, HazardType.SPEED_BREAKER, 90.0, 0.0, length=1.5, width=12.0, severity=0.5, uncertainty=0.1),
            ]
        )

        # -------------------------------------------------------------
        # 3. ADVANCED STRESS SCENARIOS
        # -------------------------------------------------------------
        self._scenarios["WRONG_SIDE_MOTORCYCLE"] = ScenarioDefinition(
            scenario_id="WRONG_SIDE_MOTORCYCLE",
            name="Wrong-Side Motorcycle",
            description="Oncoming motorcycle driving on the wrong side of the road in ego lane.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            actors=[
                ScenarioActor(401, ActorType.MOTORCYCLE, 60.0, 0.0, heading=3.14, velocity=8.0, behavior=BehaviorMode.WRONG_SIDE),
            ]
        )

        self._scenarios["MULTIPLE_CATTLE"] = ScenarioDefinition(
            scenario_id="MULTIPLE_CATTLE",
            name="Multiple Roaming Cattle",
            description="Group of cattle roaming across primary and secondary drivable channels.",
            road_type=RoadType.VILLAGE_ROAD,
            difficulty=DifficultyLevel.EXTREME,
            actors=[
                ScenarioActor(402, ActorType.CATTLE, 45.0, 1.0, heading=0.0, velocity=0.3, behavior=BehaviorMode.CRUISE),
                ScenarioActor(403, ActorType.CATTLE, 50.0, -1.5, heading=1.57, velocity=0.5, behavior=BehaviorMode.CROSSING),
                ScenarioActor(404, ActorType.CATTLE, 80.0, 0.0, heading=3.14, velocity=0.2, behavior=BehaviorMode.CRUISE),
            ]
        )

        self._scenarios["PEDESTRIAN_SWARM"] = ScenarioDefinition(
            scenario_id="PEDESTRIAN_SWARM",
            name="Pedestrian Swarm",
            description="High-density crowd of pedestrians crossing the street simultaneously.",
            road_type=RoadType.MARKET_ROAD,
            difficulty=DifficultyLevel.CHAOTIC,
            actors=[
                ScenarioActor(405 + i, ActorType.PEDESTRIAN, 40.0 + (i * 2), -3.0 + (i % 3) * 2.0, heading=1.57, velocity=1.2, behavior=BehaviorMode.CROSSING)
                for i in range(8)
            ]
        )

        self._scenarios["SUDDEN_MOTORCYCLE_CUT_IN"] = ScenarioDefinition(
            scenario_id="SUDDEN_MOTORCYCLE_CUT_IN",
            name="Sudden Motorcycle Cut-In",
            description="Fast motorcycle cutting in directly in front of ego vehicle at close range.",
            road_type=RoadType.HIGHWAY,
            difficulty=DifficultyLevel.HARD,
            actors=[
                ScenarioActor(420, ActorType.MOTORCYCLE, 25.0, -2.5, heading=0.3, velocity=9.0, behavior=BehaviorMode.SWERVING),
            ],
            events=[
                ScenarioEvent(2.0, ScenarioEventType.CHANGE_DIRECTION, {"actor_id": 420, "heading": 0.0, "y": 0.0}),
            ]
        )

        self._scenarios["BLIND_CURVE"] = ScenarioDefinition(
            scenario_id="BLIND_CURVE",
            name="Blind Curve Obstacle",
            description="Curved road segment with stationary truck obscured beyond line of sight.",
            road_type=RoadType.VILLAGE_ROAD,
            difficulty=DifficultyLevel.HARD,
            actors=[
                ScenarioActor(430, ActorType.BUS_TRUCK, 65.0, 0.5, heading=0.0, velocity=0.0, behavior=BehaviorMode.STOPPED),
            ]
        )

        self._scenarios["NARROW_ROAD"] = ScenarioDefinition(
            scenario_id="NARROW_ROAD",
            name="Narrow Single Lane Passage",
            description="Extremely narrow single-lane road passage with tight side clearance.",
            road_type=RoadType.NARROW_PASSAGE,
            difficulty=DifficultyLevel.HARD,
            actors=[
                ScenarioActor(440, ActorType.CAR, 70.0, -1.5, heading=3.14, velocity=4.0, behavior=BehaviorMode.CRUISE),
            ]
        )

        self._scenarios["TWO_OBSTACLE_CORRIDOR"] = ScenarioDefinition(
            scenario_id="TWO_OBSTACLE_CORRIDOR",
            name="Two Obstacle S-Curve Corridor",
            description="Staggered obstacles creating an S-curve negative space corridor.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            actors=[
                ScenarioActor(450, ActorType.CAR, 40.0, 1.5, heading=0.0, velocity=0.0, behavior=BehaviorMode.STOPPED),
                ScenarioActor(451, ActorType.AUTO_RICKSHAW, 65.0, -1.8, heading=0.0, velocity=0.0, behavior=BehaviorMode.STOPPED),
            ]
        )

        self._scenarios["WATER_PLUS_HIDDEN_HAZARD"] = ScenarioDefinition(
            scenario_id="WATER_PLUS_HIDDEN_HAZARD",
            name="Waterlogged Concealed Pothole",
            description="Water patch concealing a deep pothole (high surface uncertainty).",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.HARD,
            hazards=[
                ScenarioHazard(501, HazardType.WATERLOGGED, 45.0, 0.0, length=10.0, width=5.0, severity=0.7, uncertainty=0.9),
                ScenarioHazard(502, HazardType.POTHOLE, 47.0, 0.0, length=2.0, width=1.5, severity=0.9, uncertainty=0.9),
            ]
        )

        self._scenarios["TRAFFIC_PLUS_POTHOLE"] = ScenarioDefinition(
            scenario_id="TRAFFIC_PLUS_POTHOLE",
            name="Dense Traffic with Potholes",
            description="Dense moving traffic coupled with severe surface potholes.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.EXTREME,
            actors=[
                ScenarioActor(510, ActorType.AUTO_RICKSHAW, 35.0, -1.5, heading=0.0, velocity=6.0, behavior=BehaviorMode.SWERVING),
                ScenarioActor(511, ActorType.CAR, 60.0, 1.8, heading=0.0, velocity=7.0, behavior=BehaviorMode.CRUISE),
            ],
            hazards=[
                ScenarioHazard(512, HazardType.POTHOLE, 45.0, 0.5, length=2.2, width=1.5, severity=0.85, uncertainty=0.2),
            ]
        )

        self._scenarios["TRAFFIC_PLUS_WATER"] = ScenarioDefinition(
            scenario_id="TRAFFIC_PLUS_WATER",
            name="Dense Traffic with Waterlogging",
            description="Heavy traffic navigating a flooded road section.",
            road_type=RoadType.URBAN_ROAD,
            difficulty=DifficultyLevel.EXTREME,
            actors=[
                ScenarioActor(520, ActorType.BUS_TRUCK, 45.0, 1.5, heading=0.0, velocity=4.0, behavior=BehaviorMode.CRUISE),
                ScenarioActor(521, ActorType.MOTORCYCLE, 50.0, -1.5, heading=0.0, velocity=5.5, behavior=BehaviorMode.SWERVING),
            ],
            hazards=[
                ScenarioHazard(522, HazardType.WATERLOGGED, 40.0, 0.0, length=15.0, width=6.0, severity=0.65, uncertainty=0.6),
            ]
        )

        self._scenarios["MULTI_EVENT_CHAOS"] = ScenarioDefinition(
            scenario_id="MULTI_EVENT_CHAOS",
            name="Multi-Event Chaotic Road",
            description="Compounding multi-actor cut-in, cattle crossing, pothole, and sudden replanning events.",
            road_type=RoadType.MARKET_ROAD,
            difficulty=DifficultyLevel.CHAOTIC,
            actors=[
                ScenarioActor(601, ActorType.AUTO_RICKSHAW, 30.0, 1.8, heading=0.0, velocity=6.0, behavior=BehaviorMode.SWERVING),
                ScenarioActor(602, ActorType.MOTORCYCLE, 50.0, -1.8, heading=3.14, velocity=7.0, behavior=BehaviorMode.WRONG_SIDE),
            ],
            hazards=[
                ScenarioHazard(603, HazardType.POTHOLE, 40.0, 0.0, length=2.2, width=1.5, severity=0.85, uncertainty=0.2),
                ScenarioHazard(604, HazardType.WATERLOGGED, 70.0, -1.0, length=10.0, width=5.0, severity=0.7, uncertainty=0.8),
            ],
            events=[
                ScenarioEvent(2.0, ScenarioEventType.ENTER_ROAD, {"actor_id": 605, "actor_type": ActorType.CATTLE, "x": 45.0, "y": -5.0, "heading": 1.57, "velocity": 2.0}),
                ScenarioEvent(5.0, ScenarioEventType.SPAWN_OBJECT, {"actor_id": 606, "actor_type": ActorType.PEDESTRIAN, "x": 65.0, "y": 3.5, "heading": -1.57, "velocity": 1.3}),
            ],
            expected_events=[
                ExpectedEvent("EVT_01", "Chaotic multi-event obstacle cascade", "replanning", "Execute continuous adaptive replanning and emergency safety control"),
            ]
        )
