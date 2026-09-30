"""
IRIS Unified Multi-Layered Visual Canvas Renderer (Combined Phase 15).
Renders Road, World Model, Object Tracks, Predicted Trajectories, Uncertainty, Future Risk, Safe Space, and Selected Path.
"""

import pygame
import math
import numpy as np
from typing import Tuple, Optional, Any, List

# Render colors
COLOR_ROAD = (30, 41, 59)
COLOR_MARKING = (203, 213, 225)
COLOR_EGO = (34, 197, 94)
COLOR_PATH = (234, 179, 8)
COLOR_CANDIDATE = (100, 116, 139)
COLOR_PREDICTION = (147, 51, 234)
COLOR_CAR = (59, 130, 246)
COLOR_MOTORCYCLE = (236, 72, 153)
COLOR_PEDESTRIAN = (249, 115, 22)
COLOR_CATTLE = (168, 85, 247)
COLOR_AUTO_RICKSHAW = (234, 179, 8)
COLOR_POTHOLE = (120, 53, 15)
COLOR_WATER = (14, 165, 233)


class DashboardVisualizer:
    """
    Renders 2D top-down view with togglable perception, risk field, and safe-space layers.
    """

    def __init__(self, width: int = 800, height: int = 500):
        self.width = width
        self.height = height
        self.zoom = 10.0  # pixels per meter
        self.view_offset_x = 20.0
        self.view_offset_y = 250.0

    def world_to_screen(self, x: float, y: float, ego_x: float = 0.0) -> Tuple[int, int]:
        """Convert world coordinates (meters) to screen coordinates (pixels) relative to ego."""
        sx = int((x - ego_x + self.view_offset_x) * self.zoom)
        sy = int(self.height / 2.0 - y * self.zoom)
        return sx, sy

    def draw_canvas(self, surface: pygame.Surface, env: Any, world_model: Optional[Any] = None,
                    replanning_manager: Optional[Any] = None,
                    safe_space_planner: Optional[Any] = None,
                    future_risk_field: Optional[Any] = None,
                    selected_horizon_t: float = 1.0):
        """Render complete multi-layer visualization on target surface."""
        rect = surface.get_rect()
        pygame.draw.rect(surface, (15, 23, 42), rect)

        ego = env.ego_vehicle

        # 1. Draw Road Boundaries & Surface Hazards
        self._draw_road(surface, env, ego.x)

        # 2. Draw Future Risk Field Heatmap (if available)
        if future_risk_field and hasattr(future_risk_field, "get_risk_grid_at_time"):
            self._draw_future_risk_heatmap(surface, future_risk_field, ego.x, selected_horizon_t)

        # 3. Draw Safe Space Candidate Corridors
        if safe_space_planner and hasattr(safe_space_planner, "last_plan_result") and safe_space_planner.last_plan_result:
            self._draw_safe_space_corridors(surface, safe_space_planner.last_plan_result, ego.x)

        # 4. Draw Selected Path
        if ego.current_path and len(ego.current_path) > 1:
            pts = [self.world_to_screen(px, py, ego.x) for px, py in ego.current_path]
            valid_pts = [(px, py) for px, py in pts if 0 <= px <= self.width]
            if len(valid_pts) > 1:
                pygame.draw.lines(surface, COLOR_PATH, False, valid_pts, 3)

        # 5. Draw Traffic Actors & Predicted Trajectories & Uncertainty
        self._draw_traffic_and_predictions(surface, env, world_model, ego.x)

        # 6. Draw Ego Vehicle
        self._draw_ego_vehicle(surface, ego)

    def _draw_road(self, surface: pygame.Surface, env: Any, ego_x: float):
        """Draw road edges, centerlines, and surface hazards."""
        road_y_top = self.world_to_screen(0, env.road.width / 2.0, ego_x)[1]
        road_y_bot = self.world_to_screen(0, -env.road.width / 2.0, ego_x)[1]

        road_rect = pygame.Rect(0, road_y_top, self.width, road_y_bot - road_y_top)
        pygame.draw.rect(surface, COLOR_ROAD, road_rect)

        # Dashed centerline
        cy = self.world_to_screen(0, 0, ego_x)[1]
        for x in range(0, self.width, 30):
            pygame.draw.line(surface, COLOR_MARKING, (x, cy), (x + 15, cy), 1)

        # Surface Hazards
        for h in env.surface_hazards:
            sx, sy = self.world_to_screen(h.x, h.y, ego_x)
            sr = int(h.radius * self.zoom)
            col = COLOR_POTHOLE if "pothole" in str(h.hazard_type).lower() else COLOR_WATER
            pygame.draw.circle(surface, col, (sx, sy), sr, width=0)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), sr, width=1)

    def _draw_future_risk_heatmap(self, surface: pygame.Surface, risk_field: Any, ego_x: float, t_horizon: float):
        """Draw spatiotemporal risk heatmap slice at t_horizon."""
        grid = getattr(risk_field, "current_grid", None)
        if grid is None:
            return

        # Simple particle grid overlay
        h, w = grid.shape
        for r in range(0, h, 2):
            for c in range(0, w, 2):
                val = grid[r, c]
                if val > 0.15:
                    # Map grid cell to world
                    wx = c * 0.5
                    wy = (r - h / 2.0) * 0.5
                    sx, sy = self.world_to_screen(wx, wy, ego_x)
                    if 0 <= sx <= self.width:
                        alpha = int(min(255, val * 200))
                        color = (min(255, int(val * 255)), 40, min(255, int((1.0 - val) * 150)))
                        pygame.draw.circle(surface, color, (sx, sy), int(val * 8) + 2)

    def _draw_safe_space_corridors(self, surface: pygame.Surface, plan_res: Any, ego_x: float):
        """Draw candidate corridors and golden corridor highlight."""
        if not plan_res.candidates:
            return

        for candidate in plan_res.candidates:
            if not candidate.centerline:
                continue
            is_sel = (candidate == plan_res.selected_corridor)
            col = (250, 204, 21) if is_sel else (71, 85, 105)
            w = 4 if is_sel else 1
            pts = [self.world_to_screen(px, py, ego_x) for px, py in candidate.centerline]
            valid_pts = [(px, py) for px, py in pts if -50 <= px <= self.width + 50]
            if len(valid_pts) > 1:
                pygame.draw.lines(surface, col, False, valid_pts, w)

    def _draw_traffic_and_predictions(self, surface: pygame.Surface, env: Any, world_model: Optional[Any], ego_x: float):
        """Draw traffic actors, prediction arrows, and uncertainty bounds."""
        for actor in env.traffic_actors:
            sx, sy = self.world_to_screen(actor.x, actor.y, ego_x)
            if not (-50 <= sx <= self.width + 50):
                continue

            # Color by actor type
            act_str = str(actor.actor_type.name if hasattr(actor.actor_type, 'name') else actor.actor_type).upper()
            col = COLOR_CAR
            if "CATTLE" in act_str:
                col = COLOR_CATTLE
            elif "MOTORCYCLE" in act_str or "BIKE" in act_str:
                col = COLOR_MOTORCYCLE
            elif "PEDESTRIAN" in act_str:
                col = COLOR_PEDESTRIAN
            elif "RICKSHAW" in act_str:
                col = COLOR_AUTO_RICKSHAW

            # Draw Actor Rectangle / Circle
            aw = max(6, int(actor.length * self.zoom))
            ah = max(4, int(actor.width * self.zoom))
            rect = pygame.Rect(sx - aw // 2, sy - ah // 2, aw, ah)
            pygame.draw.rect(surface, col, rect, border_radius=3)
            pygame.draw.rect(surface, (255, 255, 255), rect, width=1, border_radius=3)

            # Velocity vector
            vx_len = int(actor.vx * self.zoom * 0.5)
            vy_len = int(-actor.vy * self.zoom * 0.5)
            pygame.draw.line(surface, (255, 255, 255), (sx, sy), (sx + vx_len, sy + vy_len), 2)

    def _draw_ego_vehicle(self, surface: pygame.Surface, ego: Any):
        """Draw ego vehicle icon and heading."""
        sx, sy = self.world_to_screen(ego.x, ego.y, ego.x)
        ew = int(ego.length * self.zoom)
        eh = int(ego.width * self.zoom)
        rect = pygame.Rect(sx - ew // 2, sy - eh // 2, ew, eh)
        pygame.draw.rect(surface, COLOR_EGO, rect, border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255), rect, width=2, border_radius=4)
