"""
IRIS Motion Prediction Data Models (Phase 8).
Defines dataclasses for PredictedTrajectory, PredictionHypothesis, PredictionSet,
FutureOccupiedCell, and FutureOccupancy.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from perception.object_classes import ObjectClass
from prediction.config import PREDICTION_HORIZON, PREDICTION_TIME_STEP


@dataclass
class PredictedTrajectory:
    """
    Represents a projected motion trajectory over a future time horizon for a single tracked object.
    """
    track_id: str
    object_type: Any  # ObjectClass or str
    start_position: Tuple[float, float]
    predicted_positions: List[Tuple[float, float]]
    timestamps: List[float]
    prediction_horizon: float = PREDICTION_HORIZON
    time_step: float = PREDICTION_TIME_STEP
    confidence: float = 1.0
    model_name: str = "constant_velocity"
    envelope_margins: Tuple[float, float] = (0.5, 0.5)  # (lateral_margin, longitudinal_margin)
    road_plausibility: List[bool] = field(default_factory=list)
    uncertainty_placeholder: Optional[Any] = None  # Interface reserved for Phase 9 Uncertainty Engine
    heading: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PredictedTrajectory into a dictionary representation."""
        type_str = self.object_type.name if hasattr(self.object_type, "name") else str(self.object_type)
        return {
            "track_id": self.track_id,
            "object_type": type_str,
            "start_position": self.start_position,
            "predicted_positions": self.predicted_positions,
            "timestamps": self.timestamps,
            "prediction_horizon": self.prediction_horizon,
            "time_step": self.time_step,
            "confidence": self.confidence,
            "model_name": self.model_name,
            "envelope_margins": self.envelope_margins,
            "road_plausibility": self.road_plausibility,
            "heading": self.heading,
        }


@dataclass
class PredictionHypothesis:
    """
    Represents a single behavioral hypothesis trajectory (e.g. Turn Left, Turn Right, Forward).
    """
    track_id: str
    hypothesis_id: str
    trajectory: PredictedTrajectory
    probability_placeholder: float = 1.0  # Heuristic probability weight
    behavior_type: str = "FORWARD"
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Serializes PredictionHypothesis to dictionary."""
        return {
            "track_id": self.track_id,
            "hypothesis_id": self.hypothesis_id,
            "behavior_type": self.behavior_type,
            "probability": self.probability_placeholder,
            "confidence": self.confidence,
            "trajectory": self.trajectory.to_dict(),
        }


@dataclass
class PredictionSet:
    """
    Container for all predicted trajectories and behavioral hypotheses generated in a simulation step.
    """
    timestamp: float
    prediction_horizon: float
    trajectories: List[PredictedTrajectory] = field(default_factory=list)
    hypotheses: List[PredictionHypothesis] = field(default_factory=list)
    prediction_count: int = 0

    def __post_init__(self):
        if not self.prediction_count:
            self.prediction_count = len(self.trajectories)


@dataclass
class FutureOccupiedCell:
    """
    Represents a discrete grid cell predicted to be occupied at a future timestamp t.
    """
    grid_r: int
    grid_c: int
    x_world: float
    y_world: float
    timestamp: float
    time_offset: float
    confidence: float


@dataclass
class FutureOccupancy:
    """
    Represents the spatial grid occupancy projection of a tracked object across future time steps.
    """
    track_id: str
    timestamp: float
    grid_cells: List[FutureOccupiedCell] = field(default_factory=list)
    world_positions: List[Tuple[float, float]] = field(default_factory=list)
    occupancy_confidence: float = 1.0
    hypothesis_id: str = "NOMINAL"
