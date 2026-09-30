"""
IRIS Decision State Data Structures & Enumerations (Combined Phase 13).
Defines DecisionState enum and DecisionResult dataclass.
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional, Any


class DecisionState(Enum):
    """
    High-level operational decision states for IRIS autonomous vehicle behavior.
    """
    NORMAL_DRIVING = "NORMAL_DRIVING"
    CAUTION = "CAUTION"
    SLOW_DOWN = "SLOW_DOWN"
    REPLAN = "REPLAN"
    STOP = "STOP"
    SAFETY_HOLD = "SAFETY_HOLD"
    GOAL_REACHED = "GOAL_REACHED"


@dataclass
class DecisionResult:
    """
    Structured outcome of the DecisionManager evaluation.
    """
    state: DecisionState
    target_speed_factor: float = 1.0  # Multiplier in [0.0, 1.0] applied to nominal target speed
    explanation: str = "Normal nominal navigation"
    priority_level: int = 6           # 1 (Highest safety priority) to 6 (Normal)
    override_reason: Optional[str] = None
    timestamp: float = 0.0

    @property
    def state_name(self) -> str:
        return self.state.value if isinstance(self.state, DecisionState) else str(self.state)
