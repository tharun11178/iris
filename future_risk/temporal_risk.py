"""
IRIS Temporal Risk Manager (Phase 10).
Manages time-discretization, timestep sequence generation, and temporal risk decay as objects move past.
"""

import numpy as np
from typing import List, Tuple
from future_risk.config import FUTURE_RISK_HORIZON, FUTURE_RISK_TIME_STEP


class TemporalRiskModel:
    """
    Manages temporal discretization sequence and risk evolution across time steps.
    """

    def __init__(
        self,
        horizon: float = FUTURE_RISK_HORIZON,
        time_step: float = FUTURE_RISK_TIME_STEP,
    ):
        self.horizon = horizon
        self.time_step = time_step

    def generate_timestamps(self, start_time: float = 0.0) -> List[float]:
        """
        Generates list of discrete timestamps from start_time up to horizon step.
        e.g., [0.0, 0.2, 0.4, 0.6 ... 3.0]
        """
        num_steps = int(round(self.horizon / self.time_step)) + 1
        return [round(start_time + i * self.time_step, 2) for i in range(num_steps)]

    def apply_temporal_decay(
        self,
        previous_grid: np.ndarray,
        current_grid: np.ndarray,
        decay_factor: float = 0.85,
    ) -> np.ndarray:
        """
        Ensures smooth temporal transition while allowing risk to decay once an object moves away.
        """
        # Independent timestep risk calculation with optional residual decay blend
        decayed_prev = previous_grid * decay_factor
        return np.maximum(current_grid, decayed_prev)
