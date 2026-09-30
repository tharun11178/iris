"""
IRIS Performance Metrics Dashboard Panel (Combined Phase 15).
Displays live quantitative metrics: completion, collisions, near misses, clearance, TTC, path length, smoothness.
"""

import pygame
from typing import Tuple, Optional, Any
from dashboard.panels import (
    BasePanel, COLOR_TEXT_PRIMARY, COLOR_TEXT_MUTED,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_ACCENT
)
from evaluation.scenario_metrics import ExtendedScenarioMetrics


class MetricsPanel(BasePanel):
    """
    Renders live quantitative performance KPI metrics.
    """

    def __init__(self, rect: Tuple[int, int, int, int]):
        super().__init__("📊 LIVE EVALUATION METRICS", rect)

    def draw(self, surface: pygame.Surface, metrics: Optional[ExtendedScenarioMetrics] = None):
        """Render live metrics."""
        self.draw_background(surface)

        if metrics is None:
            metrics = ExtendedScenarioMetrics()

        curr_y = self.rect.y + 40
        dy = 20

        comp_str = f"{metrics.completion_rate * 100:.0f}%"
        comp_col = COLOR_SUCCESS if metrics.completion_rate >= 0.99 else COLOR_WARNING
        self.render_kv_pair(surface, "Completion Rate", comp_str, self.rect.x + 12, curr_y, comp_col)

        curr_y += dy
        coll_col = COLOR_SUCCESS if metrics.collision_count == 0 else COLOR_DANGER
        self.render_kv_pair(surface, "Collision Count", str(metrics.collision_count), self.rect.x + 12, curr_y, coll_col)

        curr_y += dy
        near_col = COLOR_SUCCESS if metrics.near_collision_count == 0 else COLOR_WARNING
        self.render_kv_pair(surface, "Near Collisions", str(metrics.near_collision_count), self.rect.x + 12, curr_y, near_col)

        curr_y += dy
        min_clr = metrics.min_clearance_meters if metrics.min_clearance_meters < 900.0 else 0.0
        self.render_kv_pair(surface, "Min Clearance", f"{min_clr:.2f} m", self.rect.x + 12, curr_y)

        curr_y += dy
        min_ttc = metrics.min_ttc_seconds if metrics.min_ttc_seconds < 900.0 else 0.0
        self.render_kv_pair(surface, "Min TTC", f"{min_ttc:.2f} s" if min_ttc < 99.0 else "INF", self.rect.x + 12, curr_y)

        curr_y += dy
        self.render_kv_pair(surface, "Path Length", f"{metrics.total_path_length:.1f} m", self.rect.x + 12, curr_y)

        curr_y += dy
        self.render_kv_pair(surface, "Travel Time", f"{metrics.total_travel_time:.1f} s", self.rect.x + 12, curr_y)

        curr_y += dy
        self.render_kv_pair(surface, "Smoothness Score", f"{metrics.smoothness_score:.3f}", self.rect.x + 12, curr_y, COLOR_ACCENT)

        curr_y += dy
        self.render_kv_pair(surface, "Max Uncertainty", f"{metrics.max_uncertainty:.3f}", self.rect.x + 12, curr_y)

        curr_y += dy
        stops_str = f"{metrics.emergency_stops} / {metrics.safety_holds}"
        self.render_kv_pair(surface, "Emergency Stops/Hold", stops_str, self.rect.x + 12, curr_y)
