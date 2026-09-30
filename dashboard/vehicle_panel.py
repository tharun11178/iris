"""
IRIS Vehicle Telemetry Dashboard Panel (Combined Phase 15).
Displays ego vehicle state: speed, target speed, steering, acceleration, decision state, goal distance.
"""

import pygame
import math
from typing import Tuple, Optional, Any
from dashboard.panels import (
    BasePanel, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_ACCENT
)


class VehiclePanel(BasePanel):
    """
    Renders vehicle kinematic state and high-level decision control commands.
    """

    def __init__(self, rect: Tuple[int, int, int, int]):
        super().__init__("🚗 VEHICLE CONTROL & STATE", rect)

    def draw(self, surface: pygame.Surface, env: Any, decision_result: Optional[Any] = None,
             control_cmd: Optional[Any] = None):
        """Render live vehicle state."""
        self.draw_background(surface)
        ego = env.ego_vehicle

        speed_kmh = ego.velocity * 3.6
        target_speed_kmh = (control_cmd.target_speed * 3.6) if control_cmd else 0.0
        steer_deg = math.degrees(ego.steering_angle)
        accel = control_cmd.acceleration if control_cmd else 0.0
        dist_goal = max(0.0, env.road.length - ego.x)

        dec_state = decision_result.state.name if (decision_result and hasattr(decision_result.state, 'name')) else "NORMAL_DRIVING"
        
        # Color coding for state
        state_color = COLOR_SUCCESS
        if dec_state in ("SLOW_DOWN", "CAUTION"):
            state_color = COLOR_WARNING
        elif dec_state in ("STOP", "SAFETY_HOLD"):
            state_color = COLOR_DANGER

        curr_y = self.rect.y + 40
        dy = 22

        self.render_kv_pair(surface, "Decision State", dec_state, self.rect.x + 12, curr_y, state_color)
        curr_y += dy
        self.render_kv_pair(surface, "Current Speed", f"{speed_kmh:.1f} km/h", self.rect.x + 12, curr_y, COLOR_ACCENT)
        curr_y += dy
        self.render_kv_pair(surface, "Target Speed", f"{target_speed_kmh:.1f} km/h", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Steering Angle", f"{steer_deg:+.1f}°", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Acceleration", f"{accel:+.2f} m/s²", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Goal Distance", f"{dist_goal:.1f} m", self.rect.x + 12, curr_y)
