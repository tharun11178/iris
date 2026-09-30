"""
IRIS Dynamic Events & Replanning Telemetry Dashboard Panel (Combined Phase 15).
Displays replanning counts, triggers, latency, risk/clearance transitions, and recent event logs.
"""

import pygame
from typing import Tuple, Optional, Any, List
from dashboard.panels import (
    BasePanel, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_ACCENT, COLOR_CYAN
)


class EventPanel(BasePanel):
    """
    Renders replanning events and runtime scenario dynamic event logs.
    """

    def __init__(self, rect: Tuple[int, int, int, int]):
        super().__init__("🔄 REPLANNING & EVENTS LOG", rect)
        self.event_log: List[str] = []

    def add_event_log(self, text: str):
        """Append log line to recent events log."""
        self.event_log.append(text)
        if len(self.event_log) > 6:
            self.event_log.pop(0)

    def draw(self, surface: pygame.Surface, replanning_manager: Optional[Any] = None,
             scenario_runner: Optional[Any] = None):
        """Render live replanning metrics and event log."""
        self.draw_background(surface)

        replan_cnt = 0
        last_reason = "NONE"
        latency_ms = 0.0
        old_risk = 0.0
        new_risk = 0.0
        old_clearance = 0.0
        new_clearance = 0.0

        if replanning_manager:
            m = replanning_manager.metrics
            replan_cnt = m.total_replans
            latency_ms = m.avg_latency_ms

            if hasattr(replanning_manager, "history") and replanning_manager.history:
                last_evt = replanning_manager.history[-1]
                last_reason = str(last_evt.reason.name if hasattr(last_evt.reason, 'name') else last_evt.reason)
                old_risk = last_evt.old_risk
                new_risk = last_evt.new_risk
                old_clearance = last_evt.old_clearance
                new_clearance = last_evt.new_clearance

        curr_y = self.rect.y + 40
        dy = 20

        self.render_kv_pair(surface, "Total Replans", str(replan_cnt), self.rect.x + 12, curr_y, COLOR_ACCENT)
        curr_y += dy
        self.render_kv_pair(surface, "Last Reason", last_reason[:18], self.rect.x + 12, curr_y, COLOR_WARNING)
        curr_y += dy
        self.render_kv_pair(surface, "Avg Latency", f"{latency_ms:.1f} ms", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Risk Transition", f"{old_risk:.2f} ➔ {new_risk:.2f}", self.rect.x + 12, curr_y)
        curr_y += dy
        self.render_kv_pair(surface, "Clearance Shift", f"{old_clearance:.1f}m ➔ {new_clearance:.1f}m", self.rect.x + 12, curr_y)

        # Recent Event Log Box
        curr_y += dy + 5
        lbl = self.font_body.render("Recent Event Activity:", True, COLOR_TEXT_MUTED)
        surface.blit(lbl, (self.rect.x + 12, curr_y))
        curr_y += 18

        log_box = pygame.Rect(self.rect.x + 12, curr_y, self.rect.width - 24, 75)
        pygame.draw.rect(surface, (20, 27, 42), log_box, border_radius=4)
        pygame.draw.rect(surface, (51, 65, 85), log_box, width=1, border_radius=4)

        log_y = log_box.y + 4
        for line in self.event_log[-4:]:
            txt = self.font_body.render(line[:36], True, COLOR_CYAN)
            surface.blit(txt, (log_box.x + 6, log_y))
            log_y += 16
