"""
IRIS Future Risk Field Representation (Phase 10).
Defines the spatial-temporal FutureRiskField data structure storing a sequence of 2D RiskGrid matrices
across discretized future time steps t in [0.0s, 3.0s].
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional

from risk_engine.risk_grid import RiskGrid
from future_risk.config import (
    FUTURE_RISK_HORIZON,
    FUTURE_RISK_TIME_STEP,
    HIGH_RISK_THRESHOLD,
)


@dataclass
class FutureRiskField:
    """
    Spatiotemporal representation of predicted future safety risk over a time horizon.
    Maintains a discretized sequence of RiskGrid objects risk[time_index][row][col].
    """
    timestamp: float
    prediction_horizon: float = FUTURE_RISK_HORIZON
    time_step: float = FUTURE_RISK_TIME_STEP
    risk_grids: List[RiskGrid] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    active_tracks: List[str] = field(default_factory=list)
    
    # 2D summary matrices aggregated over the horizon
    peak_risk_matrix: Optional[np.ndarray] = None
    peak_time_matrix: Optional[np.ndarray] = None

    def __post_init__(self):
        """Calculates peak risk and peak time matrices over the horizon if risk_grids exist."""
        if self.risk_grids:
            num_rows = self.risk_grids[0].num_rows
            num_cols = self.risk_grids[0].num_cols
            num_steps = len(self.risk_grids)

            # Stack all total_risk 2D matrices along axis 0 to form a 3D tensor (num_steps, num_rows, num_cols)
            tensor = np.stack([grid.total_risk for grid in self.risk_grids], axis=0)

            self.peak_risk_matrix = np.max(tensor, axis=0)
            peak_indices = np.argmax(tensor, axis=0)

            # Map index to actual timestamp
            if self.timestamps:
                ts_arr = np.array(self.timestamps)
                self.peak_time_matrix = ts_arr[peak_indices]
            else:
                self.peak_time_matrix = peak_indices * self.time_step

    @property
    def num_timesteps(self) -> int:
        return len(self.risk_grids)

    @property
    def maximum_risk(self) -> float:
        """Returns peak overall risk value across all future time steps and grid cells."""
        if self.peak_risk_matrix is not None and self.peak_risk_matrix.size > 0:
            return float(np.max(self.peak_risk_matrix))
        return 0.0

    @property
    def average_risk(self) -> float:
        """Returns average spatial-temporal risk across all timesteps and cells."""
        if self.risk_grids:
            return float(np.mean([grid.get_average_risk() for grid in self.risk_grids]))
        return 0.0

    def get_risk(self, time_index: int, row: int, col: int) -> float:
        """
        Returns risk value at a specific time index and grid coordinate (row, col).
        """
        if 0 <= time_index < len(self.risk_grids):
            return self.risk_grids[time_index].get_risk(row, col)
        return 1.0  # Out of bounds time index treated as max risk

    def get_risk_at_time(self, t_offset: float, world_position: Tuple[float, float], converter: Any) -> float:
        """
        Queries risk value at a continuous time offset t (relative to sim timestamp) and world (x, y).
        Finds the closest discrete time index.
        """
        if not self.risk_grids or not self.timestamps:
            return 0.0

        # Find closest time index
        ts_diffs = [abs(t - t_offset) for t in self.timestamps]
        time_index = int(np.argmin(ts_diffs))

        row, col = converter.world_to_grid(world_position[0], world_position[1])
        return self.get_risk(time_index, row, col)

    def get_max_risk(self, time_index: int) -> float:
        """Returns peak spatial risk at a specific time index."""
        if 0 <= time_index < len(self.risk_grids):
            return self.risk_grids[time_index].get_max_risk()
        return 0.0

    def get_average_risk(self, time_index: int) -> float:
        """Returns mean spatial risk at a specific time index."""
        if 0 <= time_index < len(self.risk_grids):
            return self.risk_grids[time_index].get_average_risk()
        return 0.0

    def get_peak_risk_over_horizon(self, row: int, col: int) -> float:
        """
        Returns maximum risk value experienced at grid cell (row, col) across all future timesteps.
        """
        if self.peak_risk_matrix is not None and 0 <= row < self.peak_risk_matrix.shape[0] and 0 <= col < self.peak_risk_matrix.shape[1]:
            return float(self.peak_risk_matrix[row, col])
        return 1.0

    def get_time_of_peak_risk(self, row: int, col: int) -> float:
        """
        Returns the timestamp t when peak risk occurs at grid cell (row, col).
        """
        if self.peak_time_matrix is not None and 0 <= row < self.peak_time_matrix.shape[0] and 0 <= col < self.peak_time_matrix.shape[1]:
            return float(self.peak_time_matrix[row, col])
        return 0.0

    def is_high_risk(self, time_index: int, row: int, col: int, threshold: float = HIGH_RISK_THRESHOLD) -> bool:
        """
        Returns True if cell (row, col) at time_index exceeds high risk threshold.
        """
        return self.get_risk(time_index, row, col) >= threshold

    def get_risk_evolution(self, row: int, col: int) -> List[Tuple[float, float]]:
        """
        Returns time-series list of (timestamp, risk_value) for cell (row, col) across the horizon.
        Demonstrates temporal evolution of risk at a specific spatial location.
        """
        evolution: List[Tuple[float, float]] = []
        for idx, grid in enumerate(self.risk_grids):
            t = self.timestamps[idx] if idx < len(self.timestamps) else idx * self.time_step
            r_val = grid.get_risk(row, col)
            evolution.append((t, r_val))
        return evolution

    def to_dict(self) -> Dict[str, Any]:
        """Serializes FutureRiskField summary into dictionary."""
        return {
            "timestamp": self.timestamp,
            "prediction_horizon": self.prediction_horizon,
            "time_step": self.time_step,
            "num_timesteps": self.num_timesteps,
            "active_tracks_count": len(self.active_tracks),
            "maximum_risk": round(self.maximum_risk, 3),
            "average_risk": round(self.average_risk, 4),
        }
