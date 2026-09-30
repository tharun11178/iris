"""
IRIS Dashboard Package (Combined Phase 15).
Export visualizer, panels, and main dashboard window orchestrator.
"""

from dashboard.panels import BasePanel
from dashboard.vehicle_panel import VehiclePanel
from dashboard.risk_panel import RiskPanel
from dashboard.planning_panel import PlanningPanel
from dashboard.event_panel import EventPanel
from dashboard.metrics_panel import MetricsPanel
from dashboard.visualization import DashboardVisualizer
from dashboard.dashboard import DashboardWindow

__all__ = [
    "BasePanel",
    "VehiclePanel",
    "RiskPanel",
    "PlanningPanel",
    "EventPanel",
    "MetricsPanel",
    "DashboardVisualizer",
    "DashboardWindow",
]
