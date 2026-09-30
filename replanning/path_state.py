"""
IRIS Replanning Data Structures & Enums (Phase 12).
Defines CurrentPathState, ReplanReason, ReplanningStatus, ReplanningDecision,
ReplanEvent, and ReplanningMetrics.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Any
from planning.path import Path


class ReplanReason(Enum):
    """Enumeration of possible replanning trigger causes."""
    NO_REPLAN_REQUIRED = 0
    PATH_BLOCKED = 1          # Hard
    PREDICTED_COLLISION = 2   # Hard
    LOW_CLEARANCE = 3         # Hard / Soft
    HIGH_FUTURE_RISK = 4      # Soft
    NEW_SURFACE_HAZARD = 5    # Soft / Hard
    HIGH_UNCERTAINTY = 6      # Soft
    PATH_SCORE_DEGRADED = 7   # Soft
    PATH_DEVIATION = 8        # Soft
    GOAL_CHANGED = 9          # Hard
    PERIODIC_REFRESH = 10     # Soft
    MANUAL_REQUEST = 11       # Soft
    REPLAN_FAILED = 12        # Hard failure


class ReplanningStatus(Enum):
    """Enumeration of replanning state machine states."""
    FOLLOWING_PATH = "FOLLOWING_PATH"
    MONITORING = "MONITORING"
    REPLAN_REQUESTED = "REPLAN_REQUESTED"
    PLANNING = "PLANNING"
    PATH_VALIDATION = "PATH_VALIDATION"
    PATH_TRANSITION = "PATH_TRANSITION"
    SAFETY_HOLD = "SAFETY_HOLD"
    REPLAN_FAILED = "REPLAN_FAILED"


@dataclass
class CurrentPathState:
    """
    Structured temporal state tracking the active planned route.
    """
    path: Optional[Path] = None
    path_id: str = "PATH_INITIAL"
    creation_time: float = 0.0
    current_waypoint_index: int = 0
    remaining_distance: float = 0.0
    original_score: float = 0.0
    current_score: float = 0.0
    original_peak_risk: float = 0.0
    current_peak_risk: float = 0.0
    current_average_risk: float = 0.0
    minimum_clearance: float = 999.0
    path_valid: bool = True
    path_degraded: bool = False
    last_replan_time: float = 0.0
    replan_count: int = 0
    planner_mode: str = "iris_safe_space"
    reason_for_creation: str = "INITIAL_PLAN"
    planning_result: Optional[Any] = None
    blocked_cell_count: int = 0
    high_risk_cell_count: int = 0
    path_deviation: float = 0.0


@dataclass
class ReplanningDecision:
    """
    Structured outcome of TriggerDetector / ReplanningManager evaluation.
    """
    should_replan: bool = False
    is_hard_trigger: bool = False
    reason: ReplanReason = ReplanReason.NO_REPLAN_REQUIRED
    severity: float = 0.0
    trigger_value: float = 0.0
    threshold: float = 0.0
    timestamp: float = 0.0
    explanation: str = "Current path is safe and clear."


@dataclass
class ReplanEvent:
    """
    Log record of a completed or attempted replanning event.
    """
    event_id: str = ""
    timestamp: float = 0.0
    reason: ReplanReason = ReplanReason.NO_REPLAN_REQUIRED
    is_hard_trigger: bool = False
    trigger_value: float = 0.0
    threshold: float = 0.0
    old_path_id: str = ""
    new_path_id: str = ""
    old_score: float = 0.0
    new_score: float = 0.0
    old_peak_risk: float = 0.0
    new_peak_risk: float = 0.0
    old_clearance: float = 0.0
    new_clearance: float = 0.0
    transition_duration: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    explanation: str = ""


@dataclass
class ReplanningMetrics:
    """
    Summary metrics tracking replanning performance, counts, latency, and improvements.
    """
    total_replans: int = 0
    hard_trigger_replans: int = 0
    soft_trigger_replans: int = 0
    unnecessary_replans: int = 0
    failed_replans: int = 0
    safety_holds: int = 0
    last_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    min_latency_ms: float = 9999.0
    max_latency_ms: float = 0.0
    avg_risk_before: float = 0.0
    avg_risk_after: float = 0.0
    avg_clearance_before: float = 0.0
    avg_clearance_after: float = 0.0
    risk_improvements: List[float] = field(default_factory=list)
    clearance_improvements: List[float] = field(default_factory=list)
    score_improvements: List[float] = field(default_factory=list)
    replanning_latencies: List[float] = field(default_factory=list)
