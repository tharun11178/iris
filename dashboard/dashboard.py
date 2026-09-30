"""
IRIS Professional Telemetry Dashboard Orchestrator (Combined Phase 15).
Combines multi-layer visual canvas with Vehicle, Risk, Safe-Space, Events, and Metrics panels.
"""

import pygame
import sys
import time
from typing import Optional, Any, Dict, List

from dashboard.panels import COLOR_BG, COLOR_PANEL_BG, COLOR_BORDER, COLOR_TEXT_PRIMARY, COLOR_ACCENT
from dashboard.visualization import DashboardVisualizer
from dashboard.vehicle_panel import VehiclePanel
from dashboard.risk_panel import RiskPanel
from dashboard.planning_panel import PlanningPanel
from dashboard.event_panel import EventPanel
from dashboard.metrics_panel import MetricsPanel
from evaluation.scenario_metrics import ScenarioMetricsTracker, ExtendedScenarioMetrics


class DashboardWindow:
    """
    Main Pygame Dashboard UI window hosting multi-layered telemetry and visual canvas.
    """

    def __init__(self, width: int = 1280, height: int = 800, window_title: str = "IRIS Professional Telemetry Dashboard"):
        self.width = width
        self.height = height
        self.window_title = window_title

        pygame.init()
        pygame.display.set_caption(self.window_title)
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.clock = pygame.time.Clock()

        # Visual Canvas (Top Center)
        self.canvas_width = 780
        self.canvas_height = 460
        self.visualizer = DashboardVisualizer(width=self.canvas_width, height=self.canvas_height)
        self.canvas_surface = pygame.Surface((self.canvas_width, self.canvas_height))

        # Panel Layout Rectangles
        # Left Column: Vehicle Panel + Risk Panel
        self.vehicle_panel = VehiclePanel(rect=(15, 60, 230, 220))
        self.risk_panel = RiskPanel(rect=(15, 290, 230, 230))

        # Right Column: Planning Panel + Event Panel + Metrics Panel
        self.planning_panel = PlanningPanel(rect=(1040, 60, 225, 180))
        self.event_panel = EventPanel(rect=(1040, 250, 225, 270))

        # Bottom Bar Panel: Metrics Panel
        self.metrics_panel = MetricsPanel(rect=(15, 530, 1250, 255))

        self.paused = False
        self.font_header = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_sub = pygame.font.SysFont("Consolas", 12)

    def process_events(self) -> bool:
        """Process Pygame user events. Returns False if user requested quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_t:
                    curr_idx = self.risk_panel.selected_timestep_idx
                    self.risk_panel.set_timestep((curr_idx + 1) % len(self.risk_panel.TIMESTEPS))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.risk_panel.handle_click(event.pos)
        return True

    def render(self, env: Any, world_model: Optional[Any] = None,
               replanning_manager: Optional[Any] = None,
               safe_space_planner: Optional[Any] = None,
               future_risk_field: Optional[Any] = None,
               decision_result: Optional[Any] = None,
               control_cmd: Optional[Any] = None,
               scenario_runner: Optional[Any] = None,
               metrics: Optional[ExtendedScenarioMetrics] = None):
        """Render complete dashboard frame."""
        self.screen.fill(COLOR_BG)

        # 1. Header Bar
        hdr_rect = pygame.Rect(0, 0, self.width, 48)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, hdr_rect)
        pygame.draw.line(self.screen, COLOR_BORDER, (0, 48), (self.width, 48), 2)

        sc_name = "SIMULATION"
        sim_t = getattr(env, "sim_time", 0.0)
        if scenario_runner and scenario_runner.current_scenario:
            sc_name = scenario_runner.current_scenario.name

        fps = self.clock.get_fps()
        status_str = "PAUSED" if self.paused else f"FPS: {fps:.1f}"

        title_txt = self.font_header.render(f"IRIS DASHBOARD — Scenario: {sc_name}", True, COLOR_TEXT_PRIMARY)
        meta_txt = self.font_sub.render(f"Sim Time: {sim_t:.2f}s | {status_str} | Key T: Change Risk Horizon | SPACE: Pause", True, COLOR_ACCENT)

        self.screen.blit(title_txt, (15, 6))
        self.screen.blit(meta_txt, (15, 28))

        # 2. Render Canvas View
        t_sel = self.risk_panel.get_selected_timestep()
        self.visualizer.draw_canvas(
            self.canvas_surface, env, world_model,
            replanning_manager, safe_space_planner,
            future_risk_field, t_sel
        )
        self.screen.blit(self.canvas_surface, (250, 60))
        pygame.draw.rect(self.screen, COLOR_BORDER, (250, 60, self.canvas_width, self.canvas_height), width=1, border_radius=4)

        # 3. Render Telemetry Panels
        self.vehicle_panel.draw(self.screen, env, decision_result, control_cmd)
        self.risk_panel.draw(self.screen, replanning_manager, future_risk_field)
        self.planning_panel.draw(self.screen, safe_space_planner, env.get_minimum_clearance())
        self.event_panel.draw(self.screen, replanning_manager, scenario_runner)
        self.metrics_panel.draw(self.screen, metrics)

        pygame.display.flip()
        self.clock.tick(60)
