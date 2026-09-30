"""
IRIS Risk & Spatiotemporal Field Telemetry Dashboard Panel (Combined Phase 15).
Displays Current Risk, Future Risk, Peak Risk, Risk Evolution Timeline, and Timestep Selector.
"""

import pygame
from typing import Tuple, Optional, Any, List
from dashboard.panels import (
    BasePanel, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_CYAN, COLOR_BORDER
)


class RiskPanel(BasePanel):
    """
    Renders spatiotemporal future risk telemetry and timestep selection buttons.
    """

    TIMESTEPS = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]

    def __init__(self, rect: Tuple[int, int, int, int]):
        super().__init__("⚡ SPATIOTEMPORAL RISK FIELD", rect)
        self.selected_timestep_idx = 2  # default 1.0s
        self.risk_history: List[float] = []

    def set_timestep(self, idx: int):
        if 0 <= idx < len(self.TIMESTEPS):
            self.selected_timestep_idx = idx

    def get_selected_timestep(self) -> float:
        return self.TIMESTEPS[self.selected_timestep_idx]

    def handle_click(self, pos: Tuple[int, int]) -> bool:
        """Handle UI clicks on timestep selector buttons."""
        btn_y = self.rect.y + self.rect.height - 35
        btn_w = 40
        btn_h = 24
        start_x = self.rect.x + 12

        for i in range(len(self.TIMESTEPS)):
            bx = start_x + i * (btn_w + 6)
            btn_rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
            if btn_rect.collidepoint(pos):
                self.selected_timestep_idx = i
                return True
        return False

    def draw(self, surface: pygame.Surface, replanning_manager: Optional[Any] = None,
             future_risk_field: Optional[Any] = None):
        """Render live risk metrics and history graph."""
        self.draw_background(surface)

        curr_risk = 0.0
        peak_risk = 0.0
        if replanning_manager and replanning_manager.current_state:
            curr_risk = replanning_manager.current_state.current_peak_risk

        if future_risk_field and hasattr(future_risk_field, "get_peak_risk"):
            peak_risk = future_risk_field.get_peak_risk()
        else:
            peak_risk = curr_risk

        self.risk_history.append(curr_risk)
        if len(self.risk_history) > 60:
            self.risk_history.pop(0)

        # Risk level color
        r_color = COLOR_SUCCESS if curr_risk < 0.35 else (COLOR_WARNING if curr_risk < 0.70 else COLOR_DANGER)

        curr_y = self.rect.y + 40
        dy = 22

        self.render_kv_pair(surface, "Current Peak Risk", f"{curr_risk:.3f}", self.rect.x + 12, curr_y, r_color)
        curr_y += dy
        self.render_kv_pair(surface, "Field Max Risk", f"{peak_risk:.3f}", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Risk Level", "CRITICAL" if curr_risk > 0.7 else ("HIGH" if curr_risk > 0.4 else "LOW"), self.rect.x + 12, curr_y, r_color)

        # Mini Risk History Graph
        graph_rect = pygame.Rect(self.rect.x + 12, curr_y + 10, self.rect.width - 24, 45)
        pygame.draw.rect(surface, (20, 27, 42), graph_rect, border_radius=4)
        pygame.draw.rect(surface, COLOR_BORDER, graph_rect, width=1, border_radius=4)

        if len(self.risk_history) > 1:
            pts = []
            for i, r_val in enumerate(self.risk_history):
                gx = graph_rect.x + int(i * (graph_rect.width / max(1, len(self.risk_history) - 1)))
                gy = graph_rect.y + graph_rect.height - int(min(1.0, r_val) * (graph_rect.height - 4)) - 2
                pts.append((gx, gy))
            pygame.draw.lines(surface, r_color, False, pts, 2)

        # Timestep Selector Buttons at bottom
        btn_y = self.rect.y + self.rect.height - 35
        btn_w = 40
        btn_h = 24
        start_x = self.rect.x + 12

        ts_title = self.font_body.render("t-Horizon:", True, COLOR_TEXT_MUTED)
        surface.blit(ts_title, (start_x, btn_y - 18))

        for i, ts in enumerate(self.TIMESTEPS):
            bx = start_x + i * (btn_w + 6)
            b_rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
            is_sel = (i == self.selected_timestep_idx)
            b_bg = COLOR_CYAN if is_sel else (38, 52, 74)
            t_col = (0, 0, 0) if is_sel else COLOR_TEXT_PRIMARY

            pygame.draw.rect(surface, b_bg, b_rect, border_radius=4)
            lbl = self.font_body.render(f"{ts:.1f}s", True, t_col)
            surface.blit(lbl, (bx + 4, btn_y + 4))
