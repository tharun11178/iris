"""
IRIS Evaluation Package.
Export metrics calculator, scenario tracker, benchmark comparison, and report generator.
"""

from evaluation.metrics import MetricsCalculator, CollisionRecord, SmoothnessMetrics
from evaluation.scenario_metrics import ExtendedScenarioMetrics, ScenarioMetricsTracker
from evaluation.comparison import BenchmarkComparator
from evaluation.report import ReportGenerator

__all__ = [
    "MetricsCalculator",
    "CollisionRecord",
    "SmoothnessMetrics",
    "ExtendedScenarioMetrics",
    "ScenarioMetricsTracker",
    "BenchmarkComparator",
    "ReportGenerator",
]
