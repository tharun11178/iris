"""
IRIS Safe-Space & Planning Dashboard Panel (Combined Phase 15).
Displays negative-space drivable regions, candidate corridors, selected corridor, and clearance metrics.
"""

import pygame
from typing import Tuple, Optional, Any
from dashboard.panels import (
    BasePanel, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_ACCENT, COLOR_CYAN
)


class PlanningPanel(BasePanel):
    """
    Renders negative-space planner telemetry, clearance, and corridor selection.
    """

    def __init__(self, rect: Tuple[int, int, int, int]):
        super().__init__("🌿 SAFE-SPACE & CORRIDORS", rect)

    def draw(self, surface: pygame.Surface, safe_space_planner: Optional[Any] = None,
             clearance: float = 0.0):
        """Render live safe-space corridor metrics."""
        self.draw_background(surface)

        sel_corridor_type = "NONE"
        sel_cost = 0.0
        num_candidates = 0
        num_regions = 0

        if safe_space_planner and hasattr(safe_space_planner, "last_plan_result") and safe_space_planner.last_plan_result:
            res = safe_space_planner.last_plan_result
            if res.selected_corridor:
                sel_corridor_type = res.selected_corridor.corridor_type.name if hasattr(res.selected_corridor.corridor_type, 'name') else str(res.selected_corridor.corridor_type)
                sel_cost = res.selected_corridor.total_score
            num_candidates = len(res.candidates) if res.candidates else 0

        if safe_space_planner and hasattr(safe_space_planner, "free_space_detector"):
            num_regions = len(getattr(safe_space_planner.free_space_detector, "last_detected_regions", []))

        curr_y = self.rect.y + 40
        dy = 22

        c_color = COLOR_SUCCESS if clearance > 1.5 else (COLOR_WARNING if clearance > 0.8 else COLOR_DANGER)

        self.render_kv_pair(surface, "Selected Corridor", sel_corridor_type, self.rect.x + 12, curr_y, COLOR_ACCENT)
        curr_y += dy
        self.render_kv_pair(surface, "Corridor Cost Score", f"{sel_cost:.3f}", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Side Clearance", f"{clearance:.2f} m", self.rect.x + 12, curr_y, c_color)
        curr_y += dy
        self.render_kv_pair(surface, "Candidate Paths", str(num_candidates), self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Free Space Regions", str(num_regions), self.rect.x + 12, curr_y, COLOR_CYAN)
