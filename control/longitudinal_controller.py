"""
IRIS Longitudinal Controller (Combined Phase 13).
Proportional speed error controller calculating acceleration/deceleration commands
and normalized throttle/brake inputs.
"""

import math
from typing import Tuple
from control.config import (
    MAX_ACCELERATION,
    MAX_DECELERATION,
    EMERGENCY_DECELERATION,
    KP_LONGITUDINAL,
)


class LongitudinalController:
    """
    Longitudinal proportional controller for target speed tracking and braking commands.
    """

    def __init__(self, kp: float = KP_LONGITUDINAL):
        self.kp = kp

    def compute_longitudinal_control(
        self,
        current_speed: float,
        target_speed: float,
        dt: float = 0.05,
        is_emergency: bool = False,
    ) -> Tuple[float, float, str]:
        """
        Computes acceleration command (m/s²), throttle command [-1.0, 1.0], and braking state.
        Returns (acceleration, throttle, braking_state).
        """
        # Hard Emergency Stop
        if is_emergency or target_speed <= 0.001:
            if is_emergency:
                accel = EMERGENCY_DECELERATION
                throttle = -1.0
                braking_state = "EMERGENCY_STOP"
            else:
                accel = MAX_DECELERATION
                throttle = -1.0
                braking_state = "STOPPED"
            return accel, throttle, braking_state

        # Speed Error: e_v = v_target - v_current
        speed_error = target_speed - current_speed

        # P-Control: a = Kp * e_v
        raw_accel = self.kp * speed_error

        # Bound acceleration/deceleration commands
        if raw_accel >= 0.0:
            accel = float(min(MAX_ACCELERATION, raw_accel))
            throttle = float(accel / MAX_ACCELERATION) if MAX_ACCELERATION > 0 else 0.0
            braking_state = "ACCELERATING" if speed_error > 0.5 else "CRUISING"
        else:
            accel = float(max(MAX_DECELERATION, raw_accel))
            throttle = float(accel / abs(MAX_DECELERATION)) if MAX_DECELERATION != 0 else -1.0
            braking_state = "HARD_BRAKING" if accel < -2.5 else "MODERATE_BRAKING"

        return accel, throttle, braking_state
