"""
IRIS Uncertainty Modeling Data Structures (Phase 9).
Defines dataclasses for UncertaintyState, UncertaintyEllipse, UncertaintyRegion,
UncertaintySet, and UncertaintyGrid.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any


@dataclass
class UncertaintyState:
    """
    Structured representation of all sub-component uncertainties for a single tracked object.
    Preserves individual component scores to support detailed research analysis.
    """
    track_id: str
    object_type: Any
    position_uncertainty: float  # Normalized score [0.0, 1.0]
    velocity_uncertainty: float  # Normalized score [0.0, 1.0]
    heading_uncertainty: float   # Normalized score [0.0, 1.0]
    tracking_uncertainty: float  # Normalized score [0.0, 1.0]
    behavior_uncertainty: float  # Normalized score [0.0, 1.0]
    prediction_uncertainty: float# Normalized score [0.0, 1.0]
    perception_uncertainty: float# Normalized score [0.0, 1.0]
    overall_uncertainty: float   # Weighted aggregate score [0.0, 1.0]
    timestamp: float = 0.0
    sigma_x: float = 0.1         # Position standard deviation along X (meters)
    sigma_y: float = 0.1         # Position standard deviation along Y (meters)

    @property
    def position_sigma(self) -> float:
        return (self.sigma_x + self.sigma_y) / 2.0

    @property
    def velocity_variance(self) -> float:
        return self.velocity_uncertainty

    @property
    def behavior_disagreement(self) -> float:
        return self.behavior_uncertainty

    def to_dict(self) -> Dict[str, Any]:
        """Serializes UncertaintyState into dictionary representation."""
        type_str = self.object_type.name if hasattr(self.object_type, "name") else str(self.object_type)
        return {
            "track_id": self.track_id,
            "object_type": type_str,
            "position_uncertainty": round(self.position_uncertainty, 4),
            "velocity_uncertainty": round(self.velocity_uncertainty, 4),
            "heading_uncertainty": round(self.heading_uncertainty, 4),
            "tracking_uncertainty": round(self.tracking_uncertainty, 4),
            "behavior_uncertainty": round(self.behavior_uncertainty, 4),
            "prediction_uncertainty": round(self.prediction_uncertainty, 4),
            "perception_uncertainty": round(self.perception_uncertainty, 4),
            "overall_uncertainty": round(self.overall_uncertainty, 4),
            "timestamp": self.timestamp,
            "sigma_x": round(self.sigma_x, 4),
            "sigma_y": round(self.sigma_y, 4),
        }


class UncertaintyEllipse:
    """
    Geometric 2D uncertainty ellipse around a predicted future position.
    """
    def __init__(
        self,
        center_x: float = 0.0,
        center_y: float = 0.0,
        sigma_x: float = 0.5,
        sigma_y: float = 0.3,
        orientation_yaw: float = 0.0,
        time_offset: float = 0.0,
        confidence: float = 1.0,
        center: Optional[Tuple[float, float]] = None,
        semi_major: Optional[float] = None,
        semi_minor: Optional[float] = None,
        orientation: Optional[float] = None,
        time_horizon: Optional[float] = None,
    ):
        if center is not None:
            self.center_x, self.center_y = center
        else:
            self.center_x = center_x
            self.center_y = center_y

        if semi_major is not None and semi_minor is not None:
            self.sigma_x = semi_major
            self.sigma_y = semi_minor
        else:
            self.sigma_x = sigma_x
            self.sigma_y = sigma_y

        self.orientation_yaw = orientation if orientation is not None else orientation_yaw
        self.time_offset = time_horizon if time_horizon is not None else time_offset
        self.confidence = confidence

    @property
    def center(self) -> Tuple[float, float]:
        return (self.center_x, self.center_y)

    @property
    def semi_major(self) -> float:
        return max(self.sigma_x, self.sigma_y)

    @property
    def semi_minor(self) -> float:
        return min(self.sigma_x, self.sigma_y)

    @property
    def orientation(self) -> float:
        return self.orientation_yaw

    @property
    def time_horizon(self) -> float:
        return self.time_offset


@dataclass
class UncertaintyRegion:
    """
    Trajectory region consisting of a time-series of growing uncertainty ellipses over the horizon.
    """
    track_id: str
    timestamp: float
    ellipses: List[UncertaintyEllipse] = field(default_factory=list)
    time_offsets: List[float] = field(default_factory=list)
    state: Optional[UncertaintyState] = None
    object_type: Optional[Any] = None

    @property
    def current_ellipse(self) -> Optional[UncertaintyEllipse]:
        return self.ellipses[0] if self.ellipses else None

    @property
    def future_ellipses(self) -> List[UncertaintyEllipse]:
        return self.ellipses[1:] if len(self.ellipses) > 1 else []


class UncertaintyGrid:
    """
    2D spatial grid storing uncertainty values [0.0, 1.0] per cell across road space.
    """
    def __init__(
        self,
        num_rows: int = 40,
        num_cols: int = 140,
        grid_res: float = 0.5,
        resolution: Optional[float] = None,
    ):
        self.num_rows = num_rows
        self.num_cols = num_cols
        self.grid_res = resolution if resolution is not None else grid_res
        self.grid = np.zeros((num_rows, num_cols), dtype=np.float64)

    @property
    def uncertainty_matrix(self) -> np.ndarray:
        return self.grid

    def reset(self):
        """Resets grid to zero uncertainty."""
        self.grid.fill(0.0)

    def get_max_uncertainty(self) -> float:
        """Returns peak spatial uncertainty score."""
        return float(np.max(self.grid)) if self.grid.size > 0 else 0.0

    def get_average_uncertainty(self) -> float:
        """Returns average spatial uncertainty score."""
        return float(np.mean(self.grid)) if self.grid.size > 0 else 0.0

    def get_uncertainty(self, r: int, c: int) -> float:
        """Returns uncertainty value at cell (r, c)."""
        if 0 <= r < self.num_rows and 0 <= c < self.num_cols:
            return float(self.grid[r, c])
        return 0.0

    def get_uncertainty_at_world(self, x_world: float, y_world: float, converter: Any) -> float:
        """Returns uncertainty value at world coordinates (x_world, y_world)."""
        r, c = converter.world_to_grid(x_world, y_world)
        return self.get_uncertainty(r, c)

    def rasterize_ellipse(self, ellipse: UncertaintyEllipse, converter: Any, peak_uncertainty: float = 1.0):
        """Rasterizes Gaussian uncertainty decay inside ellipse bounds onto grid."""
        cx, cy = ellipse.center
        r_center, c_center = converter.world_to_grid(cx, cy)
        radius_cells = max(1, int(ellipse.semi_major / self.grid_res))

        r_min = max(0, r_center - radius_cells)
        r_max = min(self.num_rows, r_center + radius_cells + 1)
        c_min = max(0, c_center - radius_cells)
        c_max = min(self.num_cols, c_center + radius_cells + 1)

        for r in range(r_min, r_max):
            for c in range(c_min, c_max):
                cell_x, cell_y = converter.grid_to_world(r, c)
                dx = cell_x - cx
                dy = cell_y - cy
                dist = math.hypot(dx, dy)
                if dist <= ellipse.semi_major:
                    val = peak_uncertainty * math.exp(-0.5 * (dist / max(0.1, ellipse.semi_major)) ** 2)
                    self.grid[r, c] = max(self.grid[r, c], val)


@dataclass
class UncertaintySet:
    """
    Container storing all object uncertainty states, geometric regions, and spatial grid.
    """
    timestamp: float
    object_states: Dict[str, UncertaintyState] = field(default_factory=dict)
    regions: List[UncertaintyRegion] = field(default_factory=list)
    uncertainty_grid: Optional[UncertaintyGrid] = None

    @property
    def grid(self) -> Optional[UncertaintyGrid]:
        return self.uncertainty_grid
