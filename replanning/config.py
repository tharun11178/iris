"""
IRIS Adaptive Replanning & Dynamic Path Management Configuration (Phase 12).
Centralized parameters, replanning thresholds, trigger priorities, hysteresis,
cooldown intervals, and debug flags.
"""

from dataclasses import dataclass

# Replanning Thresholds
RISK_REPLAN_THRESHOLD: float = 0.65            # High future risk threshold for soft trigger
PEAK_RISK_INCREASE_THRESHOLD: float = 0.30     # Delta peak risk increase threshold
MIN_CLEARANCE_THRESHOLD: float = 1.1           # Minimum vehicle clearance threshold in meters
HARD_CLEARANCE_THRESHOLD: float = 0.5          # Critical hard clearance threshold in meters
UNCERTAINTY_REPLAN_THRESHOLD: float = 0.70     # High prediction uncertainty threshold
PATH_SCORE_DEGRADATION_THRESHOLD: float = 0.40 # Relative path score degradation threshold
PATH_DEVIATION_THRESHOLD: float = 3.0          # Max allowed deviation off active path in meters

# Hysteresis & Cooldown
MIN_REPLAN_INTERVAL: float = 1.0               # Minimum cooldown interval between soft replans (seconds)
MIN_IMPROVEMENT_REQUIRED: float = 0.10          # 10% minimum score improvement required to switch paths
MAX_REPLAN_COUNT: int = 100                    # Safety cap on total replan count per run

# Replanning Modes & Periodic Refresh
REPLAN_MODE: str = "EVENT_DRIVEN"              # "EVENT_DRIVEN" vs "EVENT_DRIVEN_PLUS_PERIODIC"
ENABLE_PERIODIC_REPLAN: bool = False           # Periodic safety refresh flag
PERIODIC_REPLAN_INTERVAL: float = 5.0          # Periodic safety refresh interval (seconds)

# Debug & Telemetry
REPLANNING_DEBUG: bool = True                  # Verbose replanning logging and overlay HUD flag


@dataclass
class ReplanningConfig:
    min_replan_interval: float = MIN_REPLAN_INTERVAL
    min_improvement_required: float = MIN_IMPROVEMENT_REQUIRED
    path_degradation_threshold: float = PATH_SCORE_DEGRADATION_THRESHOLD
    max_deviation_distance: float = PATH_DEVIATION_THRESHOLD
    high_risk_threshold: float = RISK_REPLAN_THRESHOLD
    hard_clearance_threshold: float = HARD_CLEARANCE_THRESHOLD
    uncertainty_threshold: float = UNCERTAINTY_REPLAN_THRESHOLD
    enable_periodic: bool = ENABLE_PERIODIC_REPLAN
    periodic_interval: float = PERIODIC_REPLAN_INTERVAL

