"""
IRIS Drivable Space Evaluator (Phase 2)
Encapsulates configurable rules that determine cell drivability and speed penalties
based on cell state, hazard type, and severity.
"""

from typing import Dict, Any, Optional
from world.cell import CellState, GridCell
from configs.sim_config import DEFAULT_DRIVABILITY_RULES


class DrivableSpaceEvaluator:
    """
    Evaluates whether a grid cell or spatial region is drivable according to configured safety rules.
    """

    def __init__(self, rules: Optional[Dict[str, bool]] = None):
        self.rules = rules if rules is not None else DEFAULT_DRIVABILITY_RULES.copy()

    def set_rule(self, state_name: str, is_drivable: bool):
        """
        Updates or overrides a drivability rule for a given cell state name.
        """
        self.rules[state_name] = is_drivable

    def evaluate_cell(self, cell: GridCell) -> bool:
        """
        Evaluates the drivability of a GridCell and sets its `is_drivable` attribute.
        Returns the boolean result.
        """
        state_key = cell.state.name
        is_drivable = self.rules.get(state_key, True)
        cell.is_drivable = is_drivable
        return is_drivable

    def get_speed_penalty(self, cell: GridCell) -> float:
        """
        Returns a speed multiplier penalty (0.0 to 1.0) for a given cell.
        1.0 = full speed allowed, 0.5 = 50% speed, 0.0 = full stop.
        """
        if not cell.is_drivable:
            return 0.0
        
        if cell.state == CellState.RAISED:
            return 0.4  # Speed breaker penalty
        elif cell.state == CellState.UNEVEN_TERRAIN:
            return 0.6  # Uneven surface penalty
        
        return 1.0
