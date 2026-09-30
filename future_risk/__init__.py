"""
IRIS Future Risk Field Package (Phase 10).
==========================================

Generates spatiotemporal FutureRiskField models combining current spatial risk,
dynamic motion predictions, Phase 9 uncertainty expansion, static surface hazard persistence,
and non-drivable boundary constraints over a 3.0s time horizon.
"""

from .config import (
    FUTURE_RISK_HORIZON,
    FUTURE_RISK_TIME_STEP,
    TRAFFIC_RISK_WEIGHT,
    SURFACE_RISK_WEIGHT,
    BOUNDARY_RISK_WEIGHT,
    COLLISION_RISK_WEIGHT,
    HYPOTHESIS_AGGREGATION_METHOD,
    OBJECT_RISK_WEIGHTS,
    HIGH_RISK_THRESHOLD,
)
from .future_risk_field import FutureRiskField
from .trajectory_risk import TrajectoryRiskModel
from .uncertainty_risk import UncertaintyRiskModel
from .surface_future_risk import SurfaceFutureRiskModel
from .temporal_risk import TemporalRiskModel
from .future_risk_engine import FutureRiskEngine

__all__ = [
    "FUTURE_RISK_HORIZON",
    "FUTURE_RISK_TIME_STEP",
    "TRAFFIC_RISK_WEIGHT",
    "SURFACE_RISK_WEIGHT",
    "BOUNDARY_RISK_WEIGHT",
    "COLLISION_RISK_WEIGHT",
    "HYPOTHESIS_AGGREGATION_METHOD",
    "OBJECT_RISK_WEIGHTS",
    "HIGH_RISK_THRESHOLD",
    "FutureRiskField",
    "TrajectoryRiskModel",
    "UncertaintyRiskModel",
    "SurfaceFutureRiskModel",
    "TemporalRiskModel",
    "FutureRiskEngine",
]
