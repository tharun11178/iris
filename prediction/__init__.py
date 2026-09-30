"""
IRIS Motion Prediction Package (Phase 8).
"""

from prediction.trajectory import (
    PredictedTrajectory,
    PredictionHypothesis,
    PredictionSet,
    FutureOccupiedCell,
    FutureOccupancy,
)
from prediction.behavior_model import (
    BehaviorCategory,
    BehaviorProfile,
    get_behavior_profile,
    classify_motion_pattern,
)
from prediction.motion_predictor import MotionPredictor
from prediction.prediction_manager import PredictionManager
import prediction.config as config

__all__ = [
    "PredictedTrajectory",
    "PredictionHypothesis",
    "PredictionSet",
    "FutureOccupiedCell",
    "FutureOccupancy",
    "BehaviorCategory",
    "BehaviorProfile",
    "get_behavior_profile",
    "classify_motion_pattern",
    "MotionPredictor",
    "PredictionManager",
    "config",
]
