"""
Pygame Renderer for IRIS Simulation Foundation (Phase 1).
Translates continuous world meters into smooth high-resolution Pygame graphics.
Features dynamic camera tracking, entity drawing, surface hazard visualization, and HUD.
"""

import pygame
import math
import numpy as np
from typing import Tuple, List

from configs.sim_config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PPM, ROAD_WIDTH, ROAD_MARGIN,
    COLOR_BACKGROUND, COLOR_GRASS, COLOR_ASPHALT, COLOR_ROAD_EDGE, COLOR_UNMARKED_CENTER,
    COLOR_EGO, COLOR_CAR, COLOR_BUS_TRUCK, COLOR_AUTO_RICKSHAW, COLOR_MOTORCYCLE,
    COLOR_PEDESTRIAN, COLOR_CATTLE, COLOR_PUSHCART, COLOR_POTHOLE, COLOR_WATERLOGGED,
    COLOR_SPEED_BREAKER, COLOR_DEBRIS
)
from simulation.entities import (
    ActorType, HazardType, BehaviorMode, SurfaceHazard, TrafficActor, EgoVehicle
)
from simulation.environment import SimulationEnvironment
from world.world_model import WorldModel
from visualization.world_view import WorldViewRenderer


class PygameRenderer:
    def __init__(self, width: int = SCREEN_WIDTH, height: int = SCREEN_HEIGHT):
        pygame.init()
        pygame.font.init()

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("IRIS — Indian Road Intelligence & Safe-space Planner (Phase 2)")

        # Fonts
        self.font_large = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 22, bold=True)
        self.font_medium = pygame.font.SysFont("Segoe UI, Arial, sans-serif", 16, bold=True)
        self.font_small = pygame.font.SysFont("Consolas, Courier New, monospace", 13)

        # Camera position in world meters
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.camera_mode = "FOLLOW"  # "FOLLOW" or "FIXED"

        # Phase 2 World Grid, Phase 4 Risk Engine, Phase 5 Surface Model, Phase 6 Perception, Phase 7 Tracking, Phase 8 Prediction, Phase 9 Uncertainty, Phase 10 Future Risk & Phase 11 Safe-Space toggles
        self.show_grid = False
        self.show_risk_heatmap = False
        self.show_risk_debug = False
        self.show_surface_debug = False
        self.show_perception_debug = False
        self.show_tracking_debug = False
        self.show_prediction_debug = False
        self.show_uncertainty_debug = False
        self.show_future_risk = False
        self.future_risk_time_index = 0
        self.show_safe_space = False
        self.show_replanning_debug = False
        self.show_control_debug = True
        self.world_view_renderer = WorldViewRenderer()

    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """
        Convert continuous world meters (x, y) to screen pixels.
        X_screen increases to the right, Y_screen increases downwards.
        World Y=0 is road center line.
        """
        center_screen_x = self.width / 3.0  # Ego vehicle positioned 1/3 across screen horizontally
        center_screen_y = self.height / 2.0

        screen_x = center_screen_x + (x - self.camera_x) * PPM
        screen_y = center_screen_y - (y - self.camera_y) * PPM  # Invert Y for screen coords
        return int(screen_x), int(screen_y)

    def render(
        self,
        env: SimulationEnvironment,
        fps: float,
        world_model: Optional[WorldModel] = None,
        path: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
        perception_manager: Optional[Any] = None,
        track_manager: Optional[Any] = None,
        prediction_manager: Optional[Any] = None,
        uncertainty_manager: Optional[Any] = None,
        future_risk_engine: Optional[Any] = None,
        safe_space_planner: Optional[Any] = None,
        replanning_manager: Optional[Any] = None,
        vehicle_controller: Optional[Any] = None,
        scenario_runner: Optional[Any] = None,
    ):
        """Render complete simulation frame."""
        # Update camera position
        if self.camera_mode == "FOLLOW":
            self.camera_x = env.ego_vehicle.x
            self.camera_y = 0.0  # Keep camera centered laterally on road axis
        else:
            self.camera_x = 50.0
            self.camera_y = 0.0

        # 1. Clear background
        self.screen.fill(COLOR_BACKGROUND)

        # 2. Draw Road and Dirt Shoulders
        self._draw_road(env)

        # 3. Draw Surface Hazards
        self._draw_surface_hazards(env.surface_hazards)

        # 4. Draw Dynamic Traffic Actors
        self._draw_traffic_actors(env.traffic_actors)

        # 5. Draw Ego Vehicle
        self._draw_ego_vehicle(env.ego_vehicle)

        # 6. Render Phase 2 World Grid Overlay if enabled
        if self.show_grid and world_model is not None:
            self.world_view_renderer.render(self.screen, world_model, self.camera_x, self.camera_y)

        # 7. Render Phase 4 Continuous Spatial Risk Heatmap if enabled
        if self.show_risk_heatmap and world_model is not None and risk_engine is not None:
            self.world_view_renderer.render_risk_heatmap(self.screen, world_model, risk_engine, self.camera_x, self.camera_y)

        # 8. Render Phase 4 Risk Component Debug Breakdown if enabled
        if self.show_risk_debug and world_model is not None and risk_engine is not None:
            self.world_view_renderer.render_risk_debug(self.screen, world_model, risk_engine)

        # 9. Render Phase 5 Road-Surface Intelligence Debug Panel if enabled
        if self.show_surface_debug and world_model is not None:
            self.world_view_renderer.render_surface_debug_panel(self.screen, world_model)

        # 10. Render Phase 6 Traffic Perception Debug View if enabled
        if self.show_perception_debug and world_model is not None:
            self.world_view_renderer.render_perception_debug(self.screen, world_model, self.camera_x, self.camera_y, perception_manager)

        # 11. Render Phase 7 Multi-Object Tracking Debug Overlay if enabled
        if self.show_tracking_debug and world_model is not None:
            self.world_view_renderer.render_tracking_debug(self.screen, world_model, self.camera_x, self.camera_y, track_manager)

        # 12. Render Phase 8 Motion Prediction Debug Overlay if enabled
        if self.show_prediction_debug and world_model is not None:
            self.world_view_renderer.render_prediction_debug(self.screen, world_model, self.camera_x, self.camera_y, prediction_manager)

        # 13. Render Phase 9 Uncertainty Modeling Debug Overlay if enabled
        if self.show_uncertainty_debug and world_model is not None:
            self.world_view_renderer.render_uncertainty_debug(self.screen, world_model, self.camera_x, self.camera_y, uncertainty_manager)

        # 14. Render Phase 10 Future Risk Field Heatmap Overlay if enabled
        if self.show_future_risk and world_model is not None:
            self.world_view_renderer.render_future_risk_field(
                self.screen, world_model, self.future_risk_time_index, self.camera_x, self.camera_y, future_risk_engine
            )

        # 15. Render Phase 11 Safe-Space / Negative-Space Planner Overlay if enabled
        if self.show_safe_space and world_model is not None:
            planning_res = getattr(world_model, "planning_result", None)
            if planning_res is None and safe_space_planner is not None and hasattr(safe_space_planner, "last_result"):
                planning_res = safe_space_planner.last_result
            space_map = getattr(world_model, "safe_space_map", None)
            if space_map is None and planning_res is not None:
                space_map = planning_res.safe_space_map

            self.world_view_renderer.render_safe_space(
                self.screen, world_model, self.camera_x, self.camera_y, safe_space_map=space_map, planning_result=planning_res
            )
            self.world_view_renderer.render_candidate_debug_panel(self.screen, planning_res)

        # 16. Render Phase 12 Adaptive Replanning Overlay & Telemetry HUD
        if replanning_manager is not None:
            self.world_view_renderer.render_replanning_overlay(
                self.screen, world_model, replanning_manager, self.camera_x, self.camera_y
            )
            if self.show_replanning_debug:
                self.world_view_renderer.render_replanning_hud(self.screen, replanning_manager)

        # 17. Render Phase 13 Decision & Vehicle Control Overlay if enabled
        if self.show_control_debug and world_model is not None:
            self.world_view_renderer.render_control_debug(
                self.screen, world_model, self.camera_x, self.camera_y, vehicle_controller
            )

        # 18. Render Phase 14 Scenario Framework HUD Panel
        if scenario_runner is not None:
            self.world_view_renderer.render_scenario_hud(self.screen, scenario_runner)

        # 19. Render Phase 3 Planned A* Trajectory
        if path is not None:
            self._draw_planned_path(path)

        # 18. Draw HUD and Overlay Statistics
        self._draw_hud(env, fps, path, risk_engine)

        pygame.display.flip()

    def _draw_planned_path(self, path: Any):
        """Render planned A* trajectory line, waypoints, and start/goal markers."""
        if not path or not path.world_points:
            if path and not path.success:
                # Banner for no safe path found
                alert_rect = pygame.Rect(self.width // 2 - 200, 95, 400, 40)
                pygame.draw.rect(self.screen, (200, 30, 30), alert_rect)
                pygame.draw.rect(self.screen, (255, 255, 255), alert_rect, 2)
                txt = self.font_medium.render("NO SAFE PATH FOUND — ROAD BLOCKED", True, (255, 255, 255))
                self.screen.blit(txt, (self.width // 2 - 180, 104))
            return

        screen_pts = [self.world_to_screen(wx, wy) for wx, wy in path.world_points]

        # Draw trajectory line
        if len(screen_pts) >= 2:
            pygame.draw.lines(self.screen, (0, 230, 255), False, screen_pts, 4)

        # Draw waypoints
        for idx, (sx, sy) in enumerate(screen_pts):
            if 0 <= sx <= self.width and 0 <= sy <= self.height:
                color = (0, 255, 200) if idx == path.current_waypoint_idx else (0, 180, 220)
                r_size = 4 if idx == path.current_waypoint_idx else 2
                pygame.draw.circle(self.screen, color, (sx, sy), r_size)

        # Start Marker (Green circle)
        sx_start, sy_start = screen_pts[0]
        if 0 <= sx_start <= self.width and 0 <= sy_start <= self.height:
            pygame.draw.circle(self.screen, (46, 204, 113), (sx_start, sy_start), 7)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx_start, sy_start), 8, 2)

        # Goal Marker (Gold star/circle)
        sx_goal, sy_goal = screen_pts[-1]
        if 0 <= sx_goal <= self.width and 0 <= sy_goal <= self.height:
            pygame.draw.circle(self.screen, (255, 215, 0), (sx_goal, sy_goal), 10)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx_goal, sy_goal), 12, 2)
            lbl = self.font_small.render("GOAL", True, (255, 215, 0))
            self.screen.blit(lbl, (sx_goal - 14, sy_goal - 26))



    def _draw_road(self, env: SimulationEnvironment):
        """Draw unstructured Indian road surface with margins and faded center markings."""
        # Calculate road boundaries on screen
        y_top_world = (ROAD_WIDTH / 2.0) + ROAD_MARGIN
        y_bottom_world = -(ROAD_WIDTH / 2.0) - ROAD_MARGIN

        _, screen_y_top = self.world_to_screen(0, y_top_world)
        _, screen_y_bottom = self.world_to_screen(0, y_bottom_world)

        # Grass Margins
        pygame.draw.rect(self.screen, COLOR_GRASS, (0, 0, self.width, self.height))

        # Main Asphalt Road Surface
        _, road_y_max = self.world_to_screen(0, ROAD_WIDTH / 2.0)
        _, road_y_min = self.world_to_screen(0, -ROAD_WIDTH / 2.0)
        road_height = road_y_min - road_y_max

        pygame.draw.rect(self.screen, COLOR_ASPHALT, (0, road_y_max, self.width, road_height))

        # Solid Road Edge Outer Lines (Unstructured edges)
        pygame.draw.line(self.screen, COLOR_ROAD_EDGE, (0, road_y_max), (self.width, road_y_max), 3)
        pygame.draw.line(self.screen, COLOR_ROAD_EDGE, (0, road_y_min), (self.width, road_y_min), 3)

        # Faded / Discontinuous Centerline (unstructured Indian road)
        _, center_y = self.world_to_screen(0, 0.0)
        dash_length_px = int(3.0 * PPM)
        dash_gap_px = int(4.0 * PPM)

        start_x_world = self.camera_x - (self.width / (2.0 * PPM))
        start_x_world = max(0.0, math.floor(start_x_world / 7.0) * 7.0)

        curr_x = start_x_world
        while curr_x < self.camera_x + (self.width / PPM):
            sx1, _ = self.world_to_screen(curr_x, 0)
            sx2, _ = self.world_to_screen(curr_x + 3.0, 0)
            pygame.draw.line(self.screen, COLOR_UNMARKED_CENTER, (sx1, center_y), (sx2, center_y), 1)
            curr_x += 7.0

    def _draw_surface_hazards(self, hazards: List[SurfaceHazard]):
        """Render potholes, waterlogged patches, speed breakers, and debris."""
        for hazard in hazards:
            sx, sy = self.world_to_screen(hazard.x, hazard.y)
            w_px = max(4, int(hazard.length * PPM))
            h_px = max(4, int(hazard.width * PPM))

            if hazard.hazard_type == HazardType.POTHOLE:
                rect = pygame.Rect(sx - w_px // 2, sy - h_px // 2, w_px, h_px)
                # Outer shadow
                pygame.draw.ellipse(self.screen, (15, 10, 8), rect)
                # Inner pothole body
                pygame.draw.ellipse(self.screen, COLOR_POTHOLE, rect.inflate(-2, -2))
                # Text label
                lbl = self.font_small.render("POTHOLE", True, (200, 160, 140))
                self.screen.blit(lbl, (sx - 20, sy - h_px // 2 - 14))

            elif hazard.hazard_type == HazardType.WATERLOGGED:
                # Create transparent surface for water
                water_surf = pygame.Surface((w_px, h_px), pygame.SRCALPHA)
                # Semi-transparent blue water (160 alpha)
                water_surf.fill((42, 123, 155, 170))
                # Add ripple lines inside
                pygame.draw.ellipse(water_surf, (80, 180, 220, 120), (2, 2, w_px - 4, h_px - 4), 2)
                self.screen.blit(water_surf, (sx - w_px // 2, sy - h_px // 2))

                # Water hazard boundary outline
                pygame.draw.rect(self.screen, (60, 160, 200), (sx - w_px // 2, sy - h_px // 2, w_px, h_px), 1)

                lbl = self.font_small.render(f"WATERLOGGED (Risk: {hazard.severity:.1f}, Uncert: {hazard.uncertainty:.1f})", True, (140, 220, 255))
                self.screen.blit(lbl, (sx - w_px // 2, sy - h_px // 2 - 14))

            elif hazard.hazard_type == HazardType.SPEED_BREAKER:
                rect = pygame.Rect(sx - w_px // 2, sy - h_px // 2, w_px, h_px)
                pygame.draw.rect(self.screen, COLOR_SPEED_BREAKER, rect)
                # Yellow-black stripes
                stripe_w = 6
                for i in range(0, w_px, stripe_w * 2):
                    s_rect = pygame.Rect(sx - w_px // 2 + i, sy - h_px // 2, stripe_w, h_px)
                    pygame.draw.rect(self.screen, (20, 20, 20), s_rect)

                lbl = self.font_small.render("SPEED BREAKER", True, (240, 220, 100))
                self.screen.blit(lbl, (sx - 35, sy - h_px // 2 - 14))

            elif hazard.hazard_type == HazardType.DEBRIS:
                rect = pygame.Rect(sx - w_px // 2, sy - h_px // 2, w_px, h_px)
                pygame.draw.rect(self.screen, COLOR_DEBRIS, rect)
                lbl = self.font_small.render("DEBRIS", True, (180, 180, 180))
                self.screen.blit(lbl, (sx - 20, sy - h_px // 2 - 14))

    def _draw_traffic_actors(self, actors: List[TrafficActor]):
        """Render multi-class dynamic road users with oriented bounding boxes."""
        color_map = {
            ActorType.CAR: COLOR_CAR,
            ActorType.BUS_TRUCK: COLOR_BUS_TRUCK,
            ActorType.AUTO_RICKSHAW: COLOR_AUTO_RICKSHAW,
            ActorType.MOTORCYCLE: COLOR_MOTORCYCLE,
            ActorType.BICYCLE: COLOR_MOTORCYCLE,
            ActorType.PEDESTRIAN: COLOR_PEDESTRIAN,
            ActorType.CATTLE: COLOR_CATTLE,
            ActorType.PUSHCART: COLOR_PUSHCART
        }

        for actor in actors:
            color = color_map.get(actor.actor_type, (200, 200, 200))
            corners_world = actor.get_corners()
            corners_screen = [self.world_to_screen(wx, wy) for wx, wy in corners_world]

            # Fill vehicle polygon
            pygame.draw.polygon(self.screen, color, corners_screen)
            pygame.draw.polygon(self.screen, (255, 255, 255), corners_screen, 1)

            # Draw heading arrow indicator
            center_sx, center_sy = self.world_to_screen(actor.x, actor.y)
            arrow_len = int(actor.length * 0.6 * PPM)
            tip_x = center_sx + int(arrow_len * math.cos(actor.heading))
            tip_y = center_sy - int(arrow_len * math.sin(actor.heading))
            pygame.draw.line(self.screen, (255, 255, 255), (center_sx, center_sy), (tip_x, tip_y), 2)

            # Label actor type and speed
            speed_kmh = actor.velocity * 3.6
            label_text = f"{actor.actor_type.name} ({speed_kmh:.0f} km/h)"
            lbl = self.font_small.render(label_text, True, (240, 240, 240))
            self.screen.blit(lbl, (center_sx - 30, center_sy - int(actor.width * PPM / 2) - 15))

    def _draw_ego_vehicle(self, ego: EgoVehicle):
        """Render Ego Autonomous Vehicle with orienting bounding box and heading line."""
        corners_world = ego.get_corners()
        corners_screen = [self.world_to_screen(wx, wy) for wx, wy in corners_world]

        # Draw vehicle body polygon
        pygame.draw.polygon(self.screen, COLOR_EGO, corners_screen)
        pygame.draw.polygon(self.screen, (255, 255, 255), corners_screen, 2)

        # Draw windshield accent
        center_sx, center_sy = self.world_to_screen(ego.x, ego.y)
        front_x = ego.x + (ego.length * 0.25) * math.cos(ego.heading)
        front_y = ego.y + (ego.length * 0.25) * math.sin(ego.heading)
        fsx, fsy = self.world_to_screen(front_x, front_y)
        pygame.draw.circle(self.screen, (220, 240, 255), (fsx, fsy), 4)

        # Draw heading direction vector line
        line_len = int(ego.length * 1.0 * PPM)
        tip_x = center_sx + int(line_len * math.cos(ego.heading))
        tip_y = center_sy - int(line_len * math.sin(ego.heading))
        pygame.draw.line(self.screen, (0, 255, 200), (center_sx, center_sy), (tip_x, tip_y), 3)

        # Ego Label
        lbl = self.font_medium.render("EGO (IRIS)", True, (255, 255, 255))
        self.screen.blit(lbl, (center_sx - 35, center_sy - int(ego.width * PPM / 2) - 20))

    def _draw_hud(
        self,
        env: SimulationEnvironment,
        fps: float,
        path: Optional[Any] = None,
        risk_engine: Optional[Any] = None,
    ):
        """Draw top banner, telemetry dashboard overlay, and status notices."""
        # Top Banner
        header_rect = pygame.Rect(0, 0, self.width, 42)
        pygame.draw.rect(self.screen, (20, 22, 28), header_rect)
        pygame.draw.line(self.screen, (60, 70, 90), (0, 42), (self.width, 42), 2)

        title_txt = self.font_large.render("IRIS — Indian Road Intelligence & Safe-space Planner", True, (255, 255, 255))
        phase_txt = self.font_medium.render("PHASE 12: Adaptive Replanning", True, (0, 240, 220))
        self.screen.blit(title_txt, (15, 8))
        self.screen.blit(phase_txt, (self.width - 320, 11))

        # Telemetry Box (Top Left)
        box_h = 160
        if path is not None:
            box_h += 20
        if risk_engine is not None and risk_engine.risk_grid is not None:
            box_h += 20

        telemetry_rect = pygame.Rect(15, 52, 300, box_h)
        surf = pygame.Surface((300, box_h), pygame.SRCALPHA)
        surf.fill((15, 18, 24, 210))  # Semi-transparent dark background
        self.screen.blit(surf, (15, 52))
        pygame.draw.rect(self.screen, (60, 80, 110), telemetry_rect, 1)

        ego = env.ego_vehicle
        speed_kmh = ego.velocity * 3.6
        heading_deg = math.degrees(ego.heading)

        lines = [
            ("SIM TIME:", f"{env.sim_time:.2f} s"),
            ("FPS:", f"{fps:.1f}"),
            ("EGO SPEED:", f"{speed_kmh:.1f} km/h ({ego.velocity:.1f} m/s)"),
            ("EGO HEADING:", f"{heading_deg:.1f}°"),
            ("EGO POSITION:", f"X={ego.x:.1f}m, Y={ego.y:.1f}m"),
            ("ACTIVE ACTORS:", f"{len(env.traffic_actors)}"),
            ("SURFACE HAZARDS:", f"{len(env.surface_hazards)}")
        ]

        if path is not None:
            p_status = "VALID" if path.valid else ("NO_PATH" if not path.success else "BLOCKED")
            p_len = f"{path.length:.1f}m ({len(path.world_points)} wpts)" if path.success else "N/A"
            lines.append(("A* PATH STATUS:", f"{p_status} | {p_len}"))

        if risk_engine is not None and risk_engine.risk_grid is not None:
            max_r = risk_engine.risk_grid.get_max_risk()
            lines.append(("PEAK RISK R(x,y):", f"{max_r:.2f} / 1.00"))

        y_offset = 60
        for label, value in lines:
            if "PATH" in label:
                c = (0, 230, 255)
            elif "RISK" in label:
                c = (231, 76, 60)
            else:
                c = (210, 225, 240)
            lbl_surf = self.font_small.render(f"{label:<16} {value}", True, c)
            self.screen.blit(lbl_surf, (25, y_offset))
            y_offset += 20

        # Off-road Warning
        if env.is_offroad:
            warn_rect = pygame.Rect(self.width // 2 - 160, 52, 320, 36)
            pygame.draw.rect(self.screen, (220, 40, 40), warn_rect)
            warn_txt = self.font_medium.render("WARNING: VEHICLE OFF ROAD BOUNDARY!", True, (255, 255, 255))
            self.screen.blit(warn_txt, (self.width // 2 - 145, 60))

        # Paused State Overlay
        if env.is_paused:
            pause_surf = self.font_large.render("[ SIMULATION PAUSED - Press SPACE to Resume ]", True, (255, 220, 0))
            self.screen.blit(pause_surf, (self.width // 2 - 220, 52))

        # Bottom Controls Legend
        legend_rect = pygame.Rect(0, self.height - 30, self.width, 30)
        pygame.draw.rect(self.screen, (18, 20, 25), legend_rect)
        legend_txt = self.font_small.render(
            "CONTROLS: [UP/DOWN] Drive  |  [R] Replan  |  [N] Safe-Space  |  [F] Future Risk  |  [U] Uncertainty  |  [M] Prediction  |  [T] Tracking  |  [G] Grid",
            True, (170, 185, 200)
        )
        self.screen.blit(legend_txt, (20, self.height - 22))

