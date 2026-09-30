"""
IRIS Scenario Definition Data Structures & Enumerations (Combined Phase 14).
Defines dataclasses and enumerations for reproducible, data-driven scenario configurations,
dynamic event specifications, expected evaluation checkpoints, and metrics metrics collection.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from simulation.entities import ActorType, HazardType, BehaviorMode


class RoadType(Enum):
    VILLAGE_ROAD = "VILLAGE_ROAD"
    URBAN_ROAD = "URBAN_ROAD"
    URBAN_INTERSECTION = "URBAN_INTERSECTION"
    HIGHWAY = "HIGHWAY"
    MARKET_ROAD = "MARKET_ROAD"
    NARROW_PASSAGE = "NARROW_PASSAGE"


class DifficultyLevel(Enum):
    EASY = "EASY"
    MODERATE = "MODERATE"
    HARD = "HARD"
    EXTREME = "EXTREME"
    CHAOTIC = "CHAOTIC"


class ScenarioEventType(Enum):
    SPAWN_OBJECT = "SPAWN_OBJECT"
    MOVE_OBJECT = "MOVE_OBJECT"
    CHANGE_DIRECTION = "CHANGE_DIRECTION"
    ENTER_ROAD = "ENTER_ROAD"
    EXIT_ROAD = "EXIT_ROAD"
    CREATE_HAZARD = "CREATE_HAZARD"
    REMOVE_HAZARD = "REMOVE_HAZARD"
    CHANGE_HAZARD = "CHANGE_HAZARD"
    CHANGE_WEATHER = "CHANGE_WEATHER"
    CHANGE_TRAFFIC_DENSITY = "CHANGE_TRAFFIC_DENSITY"


@dataclass
class ScenarioActor:
    actor_id: int
    actor_type: ActorType
    x: float
    y: float
    heading: float = 0.0
    velocity: float = 0.0
    behavior: BehaviorMode = BehaviorMode.CRUISE
    trigger_time: float = 0.0


@dataclass
class ScenarioHazard:
    hazard_id: int
    hazard_type: HazardType
    x: float
    y: float
    length: float
    width: float
    severity: float = 0.5
    uncertainty: float = 0.1


@dataclass
class ScenarioEvent:
    timestamp: float
    event_type: ScenarioEventType
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpectedEvent:
    event_id: str
    description: str
    trigger_condition: str  # e.g., "cattle_crossing", "replanning", "risk_increase", "path_change", "slowdown", "stop"
    expected_response: str
    triggered: bool = False
    timestamp_triggered: float = 0.0


@dataclass
class ScenarioMetrics:
    scenario_id: str = "UNKNOWN"
    scenario_name: str = "UNKNOWN"
    completed: bool = False
    collision_occurred: bool = False
    near_collision_count: int = 0
    min_clearance: float = 999.0
    replan_count: int = 0
    avg_replan_latency_ms: float = 0.0
    total_path_length: float = 0.0
    total_travel_time: float = 0.0
    smoothness_score: float = 1.0
    max_future_risk: float = 0.0
    max_uncertainty: float = 0.0


@dataclass
class ScenarioDefinition:
    scenario_id: str
    name: str
    description: str
    road_type: RoadType
    difficulty: DifficultyLevel
    seed: int = 42
    duration: float = 30.0
    start_pos: Tuple[float, float] = (5.0, 0.0)
    goal_pos: Tuple[float, float] = (140.0, 0.0)
    actors: List[ScenarioActor] = field(default_factory=list)
    hazards: List[ScenarioHazard] = field(default_factory=list)
    events: List[ScenarioEvent] = field(default_factory=list)
    expected_events: List[ExpectedEvent] = field(default_factory=list)
