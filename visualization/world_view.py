"""
IRIS World View Grid Renderer (Phase 2)
Provides visual overlay of the 2D spatial occupancy grid and drivable-space model
over the Pygame simulation display.
"""

import math
import pygame
from typing import Optional
from world.world_model import WorldModel
from world.cell import CellState
from configs.sim_config import (
    GRID_COLOR_DRIVABLE,
    GRID_COLOR_OCCUPIED,
    GRID_COLOR_POTHOLE,
    GRID_COLOR_WATER,
    GRID_COLOR_UNEVEN,
    GRID_COLOR_OUTSIDE,
    GRID_COLOR_BOUNDARY,
    GRID_COLOR_VEHICLE,
    GRID_COLOR_GOAL,
)


class WorldViewRenderer:
    """
    Renders 2D Occupancy & Drivable-Space Grid overlay.
    """

    def __init__(self):
        self.font = pygame.font.SysFont("Consolas", 14, bold=True)

    def render(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
    ):
        """
        Draws the discrete occupancy grid cells and goal marker.
        """
        grid = world_model.grid
        converter = world_model.converter
        ppm = converter.ppm
        grid_res = converter.grid_res

        cell_px = max(1, int(grid_res * ppm))

        # Create transparent surface overlay for smooth alpha blending
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        drivable_count = 0
        total_cells = grid.num_rows * grid.num_cols

        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                cell = grid.cells[r][c]

                if cell.is_drivable:
                    drivable_count += 1

                # Screen pixel position of top-left cell corner
                px, py = converter.world_to_screen(
                    cell.x_world - grid_res / 2.0,
                    cell.y_world - grid_res / 2.0,
                    camera_x,
                    camera_y,
                )

                # Cull out-of-screen grid cells for performance
                if px < -cell_px or px > surface.get_width() or py < -cell_px or py > surface.get_height():
                    continue

                # Color mapping per cell state
                color = GRID_COLOR_DRIVABLE
                if cell.state == CellState.OCCUPIED or cell.state == CellState.DYNAMIC_OBJECT:
                    color = GRID_COLOR_OCCUPIED
                elif cell.state == CellState.POTHOLE:
                    color = GRID_COLOR_POTHOLE
                elif cell.state == CellState.WATER:
                    color = GRID_COLOR_WATER
                elif cell.state in (CellState.UNEVEN_TERRAIN, CellState.RAISED):
                    color = GRID_COLOR_UNEVEN
                elif cell.state == CellState.OUTSIDE_ROAD:
                    color = GRID_COLOR_OUTSIDE
                elif cell.state == CellState.ROAD_BOUNDARY:
                    color = GRID_COLOR_BOUNDARY
                elif cell.state == CellState.VEHICLE:
                    color = GRID_COLOR_VEHICLE

                pygame.draw.rect(overlay, color, (px, py, cell_px, cell_px))
                pygame.draw.rect(overlay, (20, 20, 20, 30), (px, py, cell_px, cell_px), 1)

        # Draw Goal Position Marker
        goal_x, goal_y = world_model.goal_position
        g_px, g_py = converter.world_to_screen(goal_x, goal_y, camera_x, camera_y)

        if 0 <= g_px <= surface.get_width() and 0 <= g_py <= surface.get_height():
            pygame.draw.circle(overlay, GRID_COLOR_GOAL, (g_px, g_py), 12)
            pygame.draw.circle(overlay, (255, 255, 255), (g_px, g_py), 14, 2)

            goal_txt = self.font.render("GOAL", True, (255, 215, 0))
            overlay.blit(goal_txt, (g_px - 14, g_py - 28))

        # Blit transparent grid overlay onto main surface
        surface.blit(overlay, (0, 0))

        # Render World Model Legend / Stats Box (Bottom-Right)
        box_w, box_h = 320, 90
        box_x = surface.get_width() - box_w - 20
        box_y = surface.get_height() - box_h - 20

        stats_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        stats_bg.fill((15, 20, 28, 220))
        surface.blit(stats_bg, (box_x, box_y))
        pygame.draw.rect(surface, (58, 134, 255), (box_x, box_y, box_w, box_h), 2)

        drivable_pct = (drivable_count / total_cells) * 100.0 if total_cells > 0 else 0.0

        lines = [
            f"[IRIS WORLD MODEL GRID]",
            f"Grid Res: {grid_res}m ({grid.num_cols}x{grid.num_rows} cells)",
            f"Drivable Cells: {drivable_count}/{total_cells} ({drivable_pct:.1f}%)",
            f"Active Actors: {len(world_model.dynamic_actors)} | Hazards: {len(world_model.static_hazards)}",
        ]

        for i, line in enumerate(lines):
            c = (255, 255, 255) if i > 0 else (255, 215, 0)
            txt = self.font.render(line, True, c)
            surface.blit(txt, (box_x + 10, box_y + 8 + i * 19))

    def render_risk_heatmap(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        risk_engine: Any,
        camera_x: float,
        camera_y: float,
    ):
        """
        Renders Phase 4 continuous Spatial Risk Heatmap overlay over the road.
        """
        grid = world_model.grid
        converter = world_model.converter
        risk_grid = risk_engine.risk_grid

        if risk_grid is None:
            return

        grid_res = converter.grid_res
        ppm = converter.ppm
        cell_px = max(1, int(grid_res * ppm))

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                val = float(risk_grid.total_risk[r, c])
                if val <= 0.05:
                    continue  # Skip drawing very low background risk for performance

                cell = grid.cells[r][c]
                px, py = converter.world_to_screen(
                    cell.x_world - grid_res / 2.0,
                    cell.y_world - grid_res / 2.0,
                    camera_x,
                    camera_y,
                )

                if px < -cell_px or px > surface.get_width() or py < -cell_px or py > surface.get_height():
                    continue

                # Heatmap Color Gradient Mapping
                if val < 0.20:
                    color = (46, 204, 113, int(60 + val * 200))     # Green (Low)
                elif val < 0.40:
                    color = (241, 196, 15, int(80 + val * 200))     # Yellow (Moderate)
                elif val < 0.60:
                    color = (230, 126, 34, int(110 + val * 200))    # Orange (Elevated)
                elif val < 0.80:
                    color = (231, 76, 60, int(140 + val * 200))     # Red (High)
                else:
                    color = (142, 68, 173, int(180 + val * 70))     # Deep Magenta (Critical)

                pygame.draw.rect(overlay, color, (px, py, cell_px, cell_px))

        surface.blit(overlay, (0, 0))

        # Render Risk Heatmap Legend Box (Top-Right)
        box_w, box_h = 320, 100
        box_x = surface.get_width() - box_w - 20
        box_y = 52

        stats_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        stats_bg.fill((18, 15, 24, 220))
        surface.blit(stats_bg, (box_x, box_y))
        pygame.draw.rect(surface, (231, 76, 60), (box_x, box_y, box_w, box_h), 2)

        max_r = risk_grid.get_max_risk()
        avg_r = risk_grid.get_average_risk()

        lines = [
            f"[IRIS SPATIAL RISK ENGINE]",
            f"Max Risk: {max_r:.2f} | Avg Risk: {avg_r:.3f}",
            f"Weights: T={risk_engine.w_traffic:.2f} S={risk_engine.w_surface:.2f} B={risk_engine.w_boundary:.2f} C={risk_engine.w_collision:.2f}",
            f"Heatmap: 🟢Low 🟡Mod 🟧Elev 🔴High 🟣Crit",
        ]

        for i, line in enumerate(lines):
            c = (255, 255, 255) if i > 0 else (231, 76, 60)
            txt = self.font.render(line, True, c)
            surface.blit(txt, (box_x + 10, box_y + 8 + i * 21))

    def render_risk_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        risk_engine: Any,
    ):
        """
        Renders Risk Debug overlay showing exact component numerical breakdown at vehicle location.
        """
        ego = world_model.ego_state
        if not ego:
            return

        r, c = world_model.converter.world_to_grid(ego["x"], ego["y"])
        breakdown = risk_engine.get_component_risk(r, c)

        box_w, box_h = 320, 140
        box_x = 15
        box_y = surface.get_height() - box_h - 40

        dbg_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        dbg_bg.fill((10, 15, 25, 235))
        surface.blit(dbg_bg, (box_x, box_y))
        pygame.draw.rect(surface, (241, 196, 15), (box_x, box_y, box_w, box_h), 2)

        lines = [
            f"[RISK DEBUG MODE — EGO CELL ({r}, {c})]",
            f"Traffic Risk (w={risk_engine.w_traffic:.2f}):  {breakdown['traffic']:.3f}",
            f"Surface Risk (w={risk_engine.w_surface:.2f}):  {breakdown['surface']:.3f}",
            f"Boundary Risk (w={risk_engine.w_boundary:.2f}): {breakdown['boundary']:.3f}",
            f"Collision Risk (w={risk_engine.w_collision:.2f}):{breakdown['collision']:.3f}",
            f"TOTAL RISK R(x,y):        {breakdown['total']:.3f}",
        ]

        for i, line in enumerate(lines):
            c_col = (241, 196, 15) if i in (0, 5) else (220, 230, 240)
            txt = self.font.render(line, True, c_col)
            surface.blit(txt, (box_x + 10, box_y + 8 + i * 21))

    def render_surface_debug_panel(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
    ):
        """
        Renders Phase 5 Road-Surface Intelligence Debug Panel displaying
        detailed SurfaceHazard attributes (ID, Type, Size, Depth/Height, Severity, Confidence, Traversability, Risk).
        """
        surf_model = getattr(world_model, "surface_model", None)
        if surf_model is None:
            return

        ego = world_model.ego_state
        ego_x = ego.get("x", 5.0) if ego else 5.0
        ego_y = ego.get("y", 9.0) if ego else 9.0

        # Find active hazard at ego vehicle location or nearest hazard
        hazards = surf_model.get_hazards_at(ego_x, ego_y)
        active_hazard = hazards[0] if hazards else None

        if active_hazard is None and surf_model.get_hazards():
            # Find closest hazard to ego
            all_h = surf_model.get_hazards()
            all_h.sort(key=lambda h: math.hypot(h.x - ego_x, h.y - ego_y))
            active_hazard = all_h[0]

        box_w, box_h = 360, 210
        box_x = surface.get_width() - box_w - 20
        box_y = surface.get_height() - box_h - 40

        dbg_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        dbg_bg.fill((12, 20, 32, 240))
        surface.blit(dbg_bg, (box_x, box_y))
        pygame.draw.rect(surface, (0, 200, 255), (box_x, box_y, box_w, box_h), 2)

        if active_hazard is not None:
            depth_str = f"Depth: {active_hazard.depth:.2f}m" if active_hazard.depth is not None else (
                f"Height: {active_hazard.height:.2f}m" if active_hazard.height is not None else (
                    f"Roughness: {active_hazard.roughness:.2f}" if active_hazard.roughness is not None else "Depth/Height: N/A"
                )
            )
            known_str = "KNOWN" if active_hazard.underlying_surface_known else "UNKNOWN (HIDDEN HAZARD)"
            t_col = (255, 80, 80) if active_hazard.traversability.name == "NON_TRAVERSABLE" else (
                (255, 180, 0) if active_hazard.traversability.name == "RISKY" else (46, 204, 113)
            )

            lines = [
                f"[ROAD-SURFACE INTELLIGENCE — {active_hazard.hazard_id}]",
                f"Hazard Type:      {active_hazard.hazard_type.name}",
                f"Footprint Size:   {active_hazard.length:.1f}m x {active_hazard.width:.1f}m ({active_hazard.affected_area:.1f} m²)",
                f"{depth_str:<18} | Surface: {known_str}",
                f"Severity:         {active_hazard.severity:.2f} / 1.00",
                f"Confidence:       {active_hazard.confidence:.2f} / 1.00",
                f"Traversability:   {active_hazard.traversability.name}",
                f"Surface Risk:     {active_hazard.surface_risk:.2f} / 1.00",
            ]
        else:
            lines = [
                f"[ROAD-SURFACE INTELLIGENCE]",
                f"Active Surface Hazards: {len(surf_model.get_hazards())}",
                f"Status: Clear / Normal Road Surface",
                f"Surface Risk: 0.00",
                f"Traversability: SAFE",
            ]

        for i, line in enumerate(lines):
            if i == 0:
                c = (0, 230, 255)
            elif "Traversability" in line:
                c = (255, 180, 0)
            elif "Surface Risk" in line:
                c = (231, 76, 60)
            else:
                c = (220, 235, 245)
            txt = self.font.render(line, True, c)
            surface.blit(txt, (box_x + 10, box_y + 8 + i * 22))

    def render_perception_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        perception_manager: Optional[Any] = None,
    ):
        """
        Renders Phase 6 Traffic Perception Debug Visualization.
        Highlights detected objects with oriented bounding shapes, object class,
        object ID, and confidence scores.
        """
        converter = world_model.converter
        ppm = converter.ppm

        # Overlay surface for detection range ring and bounding boxes
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # 1. Draw Ego Sensor Range Ring (50m radius)
        ego = world_model.ego_state
        if ego:
            ego_wx, ego_wy = ego.get("x", 5.0), ego.get("y", 9.0)
            ego_px, ego_py = converter.world_to_screen(ego_wx, ego_wy, camera_x, camera_y)
            range_px = int(50.0 * ppm)
            pygame.draw.circle(overlay, (0, 220, 255, 30), (ego_px, ego_py), range_px, 1)

        # 2. Render Detected Object Bounding Boxes and Text Tags
        detections = perception_manager.last_detections if (perception_manager and hasattr(perception_manager, "last_detections") and perception_manager.last_detections) else []

        # Fallback to world_model dynamic actors if perception_manager empty
        if not detections:
            actors_to_draw = world_model.dynamic_actors
        else:
            actors_to_draw = [
                {
                    "id": d.object_id,
                    "type": d.object_type.name,
                    "x": d.position[0],
                    "y": d.position[1],
                    "length": d.length,
                    "width": d.width,
                    "confidence": d.confidence,
                }
                for d in detections
            ]

        for actor in actors_to_draw:
            wx, wy = actor["x"], actor["y"]
            px, py = converter.world_to_screen(wx, wy, camera_x, camera_y)

            # Cull out-of-screen objects
            if px < -50 or px > surface.get_width() + 50 or py < -50 or py > surface.get_height() + 50:
                continue

            length = actor.get("length", 2.0)
            width = actor.get("width", 1.0)
            l_px = max(10, int(length * ppm))
            w_px = max(10, int(width * ppm))

            # Bounding box rect centered at (px, py)
            box_rect = pygame.Rect(px - l_px // 2, py - w_px // 2, l_px, w_px)

            # Draw transparent box background and cyan bounding outline
            pygame.draw.rect(overlay, (0, 230, 255, 50), box_rect)
            pygame.draw.rect(overlay, (0, 240, 255, 230), box_rect, 2)

            # Corner crosshair ticks
            c_len = 4
            pygame.draw.line(overlay, (255, 255, 255), (box_rect.left, box_rect.top), (box_rect.left + c_len, box_rect.top), 2)
            pygame.draw.line(overlay, (255, 255, 255), (box_rect.left, box_rect.top), (box_rect.left, box_rect.top + c_len), 2)
            pygame.draw.line(overlay, (255, 255, 255), (box_rect.right, box_rect.bottom), (box_rect.right - c_len, box_rect.bottom), 2)
            pygame.draw.line(overlay, (255, 255, 255), (box_rect.right, box_rect.bottom), (box_rect.right, box_rect.bottom - c_len), 2)

            # Text label above bounding box
            a_type = actor.get("type", "UNKNOWN")
            a_id = actor.get("id", "OBJ_000")
            conf = actor.get("confidence", 0.95)

            tag_str = f"{a_type} | {a_id} | {conf:.2f}"
            lbl = self.font.render(tag_str, True, (0, 255, 230))

            lbl_bg = pygame.Surface((lbl.get_width() + 6, lbl.get_height() + 2), pygame.SRCALPHA)
            lbl_bg.fill((10, 20, 30, 220))
            overlay.blit(lbl_bg, (px - lbl.get_width() // 2 - 3, box_rect.top - 20))
            overlay.blit(lbl, (px - lbl.get_width() // 2, box_rect.top - 19))

        surface.blit(overlay, (0, 0))

        # 3. Perception HUD Summary Panel (Top Right)
        panel_w, panel_h = 320, 110
        panel_x = surface.get_width() - panel_w - 20
        panel_y = 60

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((10, 25, 40, 230))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (0, 220, 255), (panel_x, panel_y, panel_w, panel_h), 2)

        lines = [
            "[TRAFFIC PERCEPTION ENGINE — PHASE 6]",
            f"Active Detections: {len(actors_to_draw)} objects",
            f"Sensor Range:      50.0 meters",
            f"Pipeline Source:   SimulatedDetector (Synthetic)",
            f"Perception State:  VALIDATED & ACTIVE",
        ]

        for i, line in enumerate(lines):
            c = (0, 230, 255) if i == 0 else ((46, 204, 113) if i == 4 else (220, 235, 245))
            txt = self.font.render(line, True, c)
            surface.blit(txt, (panel_x + 10, panel_y + 8 + i * 19))

    def render_tracking_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        track_manager: Optional[Any] = None,
    ):
        """
        Renders Phase 7 Multi-Object Tracking Debug Overlay.
        Draws bounding box with state-based coloring, track ID, speed, confidence,
        and short historical position trails explicitly labeled as HISTORY.
        """
        converter = world_model.converter
        ppm = converter.ppm

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # 1. Draw Ego Sensor Range Ring (50m radius)
        ego = world_model.ego_state
        if ego:
            ego_wx, ego_wy = ego.get("x", 5.0), ego.get("y", 9.0)
            ego_px, ego_py = converter.world_to_screen(ego_wx, ego_wy, camera_x, camera_y)
            range_px = int(50.0 * ppm)
            pygame.draw.circle(overlay, (0, 220, 255, 30), (ego_px, ego_py), range_px, 1)

        # 2. Get active tracks from track_manager or world_model.dynamic_actors
        tracks_to_draw = []
        if track_manager is not None and hasattr(track_manager, "get_active_tracks"):
            tracks_to_draw = track_manager.get_active_tracks()
        elif world_model is not None:
            # Fallback to dynamic actors containing 'track' object or dict representation
            for actor in world_model.dynamic_actors:
                if "track" in actor:
                    tracks_to_draw.append(actor["track"])

        for track in tracks_to_draw:
            wx, wy = track.current_position
            px, py = converter.world_to_screen(wx, wy, camera_x, camera_y)

            # Cull out-of-screen objects
            if px < -60 or px > surface.get_width() + 60 or py < -60 or py > surface.get_height() + 60:
                continue

            length = getattr(track, "length", 2.0)
            width = getattr(track, "width", 1.0)
            l_px = max(12, int(length * ppm))
            w_px = max(12, int(width * ppm))

            state_name = track.state.name if hasattr(track.state, "name") else str(track.state)

            # State-Based Bounding Box Color Scheme
            if state_name == "CONFIRMED":
                box_color = (0, 240, 180)     # Bright Cyan / Green
                bg_color = (0, 240, 180, 40)
            elif state_name == "TENTATIVE":
                box_color = (241, 196, 15)    # Yellow
                bg_color = (241, 196, 15, 40)
            else:  # LOST
                box_color = (230, 126, 34)    # Orange
                bg_color = (230, 126, 34, 40)

            # A. Render Historical Trail (HISTORY, not prediction)
            if hasattr(track, "history") and track.history and len(track.history) >= 2:
                trail_pts = []
                for hx, hy in track.history:
                    h_px, h_py = converter.world_to_screen(hx, hy, camera_x, camera_y)
                    trail_pts.append((h_px, h_py))

                if len(trail_pts) >= 2:
                    pygame.draw.lines(overlay, (0, 200, 255, 160), False, trail_pts, 2)
                    for tx, ty in trail_pts[:-1]:
                        pygame.draw.circle(overlay, (0, 200, 255, 180), (tx, ty), 2)

                # Label oldest trail point as HISTORY
                if trail_pts:
                    oldest_x, oldest_y = trail_pts[0]
                    h_lbl = self.font.render("HISTORY", True, (140, 200, 230))
                    overlay.blit(h_lbl, (oldest_x - 20, oldest_y - 12))

            # B. Bounding Box & Current Position Dot
            box_rect = pygame.Rect(px - l_px // 2, py - w_px // 2, l_px, w_px)
            pygame.draw.rect(overlay, bg_color, box_rect)
            pygame.draw.rect(overlay, box_color, box_rect, 2)
            pygame.draw.circle(overlay, box_color, (px, py), 4)

            # C. Track Tag: ID, Class, Speed, Confidence, State
            a_type = track.object_type.name if hasattr(track.object_type, "name") else str(track.object_type)
            speed_kmh = track.speed * 3.6
            tag_str = f"{track.track_id} | {a_type} | {speed_kmh:.1f} km/h | {track.confidence:.2f} [{state_name}]"
            lbl = self.font.render(tag_str, True, (255, 255, 255))

            lbl_bg = pygame.Surface((lbl.get_width() + 8, lbl.get_height() + 4), pygame.SRCALPHA)
            lbl_bg.fill((12, 18, 28, 230))
            overlay.blit(lbl_bg, (px - lbl.get_width() // 2 - 4, box_rect.top - 22))
            overlay.blit(lbl, (px - lbl.get_width() // 2, box_rect.top - 20))

        surface.blit(overlay, (0, 0))

        # 3. Multi-Object Tracker HUD Summary Panel (Top Right)
        panel_w, panel_h = 360, 130
        panel_x = surface.get_width() - panel_w - 20
        panel_y = 60

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((10, 20, 32, 235))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (0, 240, 180), (panel_x, panel_y, panel_w, panel_h), 2)

        summary = track_manager.get_summary() if track_manager and hasattr(track_manager, "get_summary") else {
            "total_active": len(tracks_to_draw),
            "confirmed_count": sum(1 for t in tracks_to_draw if getattr(t, "state", "").name == "CONFIRMED"),
            "tentative_count": sum(1 for t in tracks_to_draw if getattr(t, "state", "").name == "TENTATIVE"),
            "lost_count": sum(1 for t in tracks_to_draw if getattr(t, "state", "").name == "LOST"),
            "total_created": len(tracks_to_draw),
            "total_deleted": 0,
        }

        lines = [
            "[MULTI-OBJECT TRACKER — PHASE 7]",
            f"Active Tracks:    {summary['total_active']} (Confirmed: {summary['confirmed_count']}, Tent: {summary['tentative_count']}, Lost: {summary['lost_count']})",
            f"Tracks Lifetime:  Created: {summary['total_created']} | Deleted: {summary['total_deleted']}",
            f"Data Association: Class-Aware Spatial Distance (Greedy)",
            f"Velocity Estim:   Smoothed Exponential (alpha=0.60)",
        ]

        for i, line in enumerate(lines):
            c = (0, 240, 180) if i == 0 else ((46, 204, 113) if i == 1 else (220, 235, 245))
            txt = self.font.render(line, True, c)
            surface.blit(txt, (panel_x + 10, panel_y + 8 + i * 22))

    def render_prediction_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        prediction_manager: Optional[Any] = None,
    ):
        """
        Renders Phase 8 Motion Prediction Debug Overlay.
        Draws dashed trajectory lines, geometric envelope boundaries, multi-hypothesis branches
        (H1, H2, H3), and motion prediction telemetry HUD.
        """
        converter = world_model.converter
        ppm = converter.ppm

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        pred_set = None
        if prediction_manager is not None and hasattr(prediction_manager, "last_prediction_set"):
            pred_set = prediction_manager.last_prediction_set
        elif world_model is not None and hasattr(world_model, "prediction_set"):
            pred_set = world_model.prediction_set

        if pred_set is not None:
            # 1. Render Nominal Trajectories & Geometric Envelopes
            for traj in pred_set.trajectories:
                sx0, sy0 = converter.world_to_screen(traj.start_position[0], traj.start_position[1], camera_x, camera_y)
                points = [(sx0, sy0)]

                for px, py in traj.predicted_positions:
                    psx, psy = converter.world_to_screen(px, py, camera_x, camera_y)
                    points.append((psx, psy))

                # Draw dashed nominal prediction line in Magenta/Purple
                if len(points) >= 2:
                    for k in range(len(points) - 1):
                        p1 = points[k]
                        p2 = points[k + 1]
                        pygame.draw.line(overlay, (220, 100, 255, 200), p1, p2, 2)
                        pygame.draw.circle(overlay, (240, 140, 255, 220), p2, 3)

                # Draw Envelope (translucent margin rect at final predicted position)
                if traj.predicted_positions:
                    last_wx, last_wy = traj.predicted_positions[-1]
                    l_px, l_py = converter.world_to_screen(last_wx, last_wy, camera_x, camera_y)
                    lat_margin, long_margin = traj.envelope_margins
                    w_px = max(10, int(lat_margin * 2.0 * ppm))
                    h_px = max(10, int(long_margin * 2.0 * ppm))

                    env_rect = pygame.Rect(l_px - w_px // 2, l_py - h_px // 2, w_px, h_px)
                    pygame.draw.rect(overlay, (220, 100, 255, 35), env_rect)
                    pygame.draw.rect(overlay, (240, 120, 255, 180), env_rect, 1)

                    lbl = self.font.render("PREDICTION", True, (240, 140, 255))
                    overlay.blit(lbl, (l_px - 25, l_py - 20))

            # 2. Render Multi-Hypothesis Trajectories (e.g. Cattle, Pedestrians)
            for hypo in pred_set.hypotheses:
                traj = hypo.trajectory
                sx0, sy0 = converter.world_to_screen(traj.start_position[0], traj.start_position[1], camera_x, camera_y)
                points = [(sx0, sy0)]

                for px, py in traj.predicted_positions:
                    psx, psy = converter.world_to_screen(px, py, camera_x, camera_y)
                    points.append((psx, psy))

                # Hypothesis color mapping
                if hypo.hypothesis_id == "H1":
                    h_color = (46, 204, 113)   # Green (Forward)
                elif hypo.hypothesis_id == "H2":
                    h_color = (54, 162, 235)   # Cyan (Turn Left)
                else:
                    h_color = (255, 159, 64)   # Orange (Turn Right)

                if len(points) >= 2:
                    pygame.draw.lines(overlay, (*h_color, 180), False, points, 2)
                    for pt in points[1::2]:
                        pygame.draw.circle(overlay, (*h_color, 220), pt, 3)

                if points:
                    end_px, end_py = points[-1]
                    h_lbl = self.font.render(f"{hypo.hypothesis_id}: {hypo.behavior_type}", True, h_color)
                    overlay.blit(h_lbl, (end_px - 30, end_py - 15))

        surface.blit(overlay, (0, 0))

        # 3. Motion Prediction HUD Summary Panel (Top Right)
        panel_w, panel_h = 360, 130
        panel_x = surface.get_width() - panel_w - 20
        panel_y = 60

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((20, 12, 32, 235))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (220, 100, 255), (panel_x, panel_y, panel_w, panel_h), 2)

        summary = prediction_manager.get_summary() if prediction_manager and hasattr(prediction_manager, "get_summary") else {
            "total_trajectories": len(pred_set.trajectories) if pred_set else 0,
            "total_hypotheses": len(pred_set.hypotheses) if pred_set else 0,
            "future_occupancies_count": len(world_model.future_occupancies) if world_model else 0,
        }

        lines = [
            "[MOTION PREDICTION ENGINE — PHASE 8]",
            f"Prediction Horizon: 3.0s (step=0.2s)",
            f"Active Nominal Trajectories: {summary['total_trajectories']}",
            f"Multi-Hypotheses Branches:   {summary['total_hypotheses']}",
            f"Future Occupancy Grid Cells: {summary['future_occupancies_count']}",
        ]

        for i, line in enumerate(lines):
            c = (220, 100, 255) if i == 0 else ((46, 204, 113) if i in (2, 3) else (230, 235, 245))
            txt = self.font.render(line, True, c)
            surface.blit(txt, (panel_x + 10, panel_y + 8 + i * 22))

    def render_uncertainty_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        uncertainty_manager: Optional[Any] = None,
    ):
        """
        Renders Phase 9 Uncertainty Modeling Debug Overlay.
        Draws position/prediction uncertainty ellipses growing over time,
        multi-hypothesis spatial dispersion regions, and uncertainty HUD.
        """
        converter = world_model.converter
        ppm = converter.ppm

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        u_set = None
        if uncertainty_manager is not None and hasattr(uncertainty_manager, "last_uncertainty_set"):
            u_set = uncertainty_manager.last_uncertainty_set
        elif world_model is not None and hasattr(world_model, "uncertainty_set"):
            u_set = world_model.uncertainty_set

        if u_set is not None and u_set.regions:
            for region in u_set.regions:
                # 1. Render Current-Time Uncertainty Ellipse
                current_ellipse = region.current_ellipse
                c_x, c_y = current_ellipse.center
                px, py = converter.world_to_screen(c_x, c_y, camera_x, camera_y)

                if -100 <= px <= surface.get_width() + 100 and -100 <= py <= surface.get_height() + 100:
                    a_px = max(6, int(current_ellipse.semi_major * ppm))
                    b_px = max(6, int(current_ellipse.semi_minor * ppm))

                    # Render rotated ellipse surface
                    ellipse_surf = pygame.Surface((a_px * 2 + 10, b_px * 2 + 10), pygame.SRCALPHA)
                    rect = pygame.Rect(5, 5, a_px * 2, b_px * 2)

                    # Gradient color based on overall uncertainty
                    u_val = region.state.overall_uncertainty
                    if u_val < 0.3:
                        u_color = (255, 200, 0)       # Amber/Yellow
                    elif u_val < 0.6:
                        u_color = (255, 120, 0)       # Orange
                    else:
                        u_color = (255, 40, 40)        # Bright Red

                    pygame.draw.ellipse(ellipse_surf, (*u_color, 45), rect)
                    pygame.draw.ellipse(ellipse_surf, (*u_color, 220), rect, 2)

                    # Rotation angle in degrees (Pygame rotates counter-clockwise in degrees)
                    rot_deg = math.degrees(current_ellipse.orientation)
                    rot_surf = pygame.transform.rotate(ellipse_surf, rot_deg)
                    rot_rect = rot_surf.get_rect(center=(px, py))
                    overlay.blit(rot_surf, rot_rect)

                    # Label
                    st = region.state
                    tag_str = f"{region.track_id} | U={st.overall_uncertainty:.2f} (Pos:{st.position_sigma:.2f} Vel:{st.velocity_variance:.2f} Beh:{st.behavior_disagreement:.2f})"
                    lbl = self.font.render(tag_str, True, (255, 220, 100))
                    lbl_bg = pygame.Surface((lbl.get_width() + 6, lbl.get_height() + 2), pygame.SRCALPHA)
                    lbl_bg.fill((20, 15, 10, 220))
                    overlay.blit(lbl_bg, (px - lbl.get_width() // 2 - 3, rot_rect.top - 20))
                    overlay.blit(lbl, (px - lbl.get_width() // 2, rot_rect.top - 19))

                # 2. Render Future Horizon Growing Ellipses (t=1.0s, t=2.0s, t=3.0s)
                for f_ellipse in region.future_ellipses:
                    fc_x, fc_y = f_ellipse.center
                    fpx, fpy = converter.world_to_screen(fc_x, fc_y, camera_x, camera_y)

                    if -100 <= fpx <= surface.get_width() + 100 and -100 <= fpy <= surface.get_height() + 100:
                        fa_px = max(8, int(f_ellipse.semi_major * ppm))
                        fb_px = max(8, int(f_ellipse.semi_minor * ppm))

                        f_ellipse_surf = pygame.Surface((fa_px * 2 + 10, fb_px * 2 + 10), pygame.SRCALPHA)
                        f_rect = pygame.Rect(5, 5, fa_px * 2, fb_px * 2)

                        pygame.draw.ellipse(f_ellipse_surf, (255, 165, 0, 30), f_rect)
                        pygame.draw.ellipse(f_ellipse_surf, (255, 185, 50, 160), f_rect, 1)

                        rot_deg = math.degrees(f_ellipse.orientation)
                        f_rot_surf = pygame.transform.rotate(f_ellipse_surf, rot_deg)
                        f_rot_rect = f_rot_surf.get_rect(center=(fpx, fpy))
                        overlay.blit(f_rot_surf, f_rot_rect)

                        # Horizon stamp label
                        h_txt = self.font.render(f"t+{f_ellipse.time_horizon:.1f}s", True, (255, 200, 120))
                        overlay.blit(h_txt, (fpx - 15, fpy - 10))

        surface.blit(overlay, (0, 0))

        # 3. Uncertainty HUD Summary Panel (Top Right)
        panel_w, panel_h = 360, 140
        panel_x = surface.get_width() - panel_w - 20
        panel_y = 60

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((30, 20, 10, 235))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (255, 165, 0), (panel_x, panel_y, panel_w, panel_h), 2)

        summary = uncertainty_manager.get_summary() if uncertainty_manager and hasattr(uncertainty_manager, "get_summary") else {
            "active_regions": len(u_set.regions) if u_set else 0,
            "avg_overall_uncertainty": sum(r.state.overall_uncertainty for r in u_set.regions)/len(u_set.regions) if u_set and u_set.regions else 0.0,
            "avg_position_sigma": sum(r.state.position_sigma for r in u_set.regions)/len(u_set.regions) if u_set and u_set.regions else 0.0,
            "avg_velocity_variance": sum(r.state.velocity_variance for r in u_set.regions)/len(u_set.regions) if u_set and u_set.regions else 0.0,
            "grid_cells_count": u_set.grid.uncertainty_matrix.size if (u_set and u_set.grid and u_set.grid.uncertainty_matrix is not None) else 0,
        }

        lines = [
            "[UNCERTAINTY MODELING — PHASE 9]",
            f"Active Regions:       {summary['active_regions']}",
            f"Mean Uncertainty:     {summary['avg_overall_uncertainty']:.3f} / 1.00",
            f"Mean Pos Sigma:       {summary['avg_position_sigma']:.3f} m",
            f"Mean Vel Variance:    {summary['avg_velocity_variance']:.3f} m²/s²",
            f"Horizon Growth Rate:  0.10 / sec (Linear)",
        ]

        for i, line in enumerate(lines):
            c = (255, 165, 0) if i == 0 else ((46, 204, 113) if i in (1, 2) else (240, 235, 230))
            txt = self.font.render(line, True, c)
            surface.blit(txt, (panel_x + 10, panel_y + 8 + i * 21))

    def render_future_risk_field(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        time_index: int,
        camera_x: float,
        camera_y: float,
        future_risk_engine: Optional[Any] = None,
    ):
        """
        Renders Phase 10 Spatiotemporal Future Risk Field Heatmap Overlay at specified time_index.
        """
        grid = world_model.grid
        converter = world_model.converter

        field = getattr(world_model, "future_risk_field", None)
        if field is None and future_risk_engine is not None and hasattr(future_risk_engine, "last_risk_field"):
            field = future_risk_engine.last_risk_field

        if field is None or not field.risk_grids:
            return

        time_index = max(0, min(time_index, len(field.risk_grids) - 1))
        risk_grid = field.risk_grids[time_index]
        t_val = field.timestamps[time_index] if time_index < len(field.timestamps) else time_index * field.time_step

        grid_res = converter.grid_res
        ppm = converter.ppm
        cell_px = max(1, int(grid_res * ppm))

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        for r in range(grid.num_rows):
            for c in range(grid.num_cols):
                val = float(risk_grid.total_risk[r, c])
                if val <= 0.05:
                    continue  # Skip low risk background cells

                cell = grid.cells[r][c]
                px, py = converter.world_to_screen(
                    cell.x_world - grid_res / 2.0,
                    cell.y_world - grid_res / 2.0,
                    camera_x,
                    camera_y,
                )

                if px < -cell_px or px > surface.get_width() or py < -cell_px or py > surface.get_height():
                    continue

                # Heatmap Color Gradient Mapping
                if val < 0.20:
                    color = (46, 204, 113, int(60 + val * 200))     # Green (Low)
                elif val < 0.40:
                    color = (241, 196, 15, int(80 + val * 200))     # Yellow (Moderate)
                elif val < 0.60:
                    color = (230, 126, 34, int(110 + val * 200))    # Orange (Elevated)
                elif val < 0.80:
                    color = (231, 76, 60, int(140 + val * 200))     # Red (High)
                else:
                    color = (155, 44, 240, int(180 + val * 70))     # Vivid Purple/Magenta (Critical)

                pygame.draw.rect(overlay, color, (px, py, cell_px, cell_px))

        surface.blit(overlay, (0, 0))

        # Render Future Risk HUD Summary Panel (Top Right)
        box_w, box_h = 360, 150
        box_x = surface.get_width() - box_w - 20
        box_y = 52

        stats_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        stats_bg.fill((22, 12, 34, 235))
        surface.blit(stats_bg, (box_x, box_y))
        pygame.draw.rect(surface, (155, 44, 240), (box_x, box_y, box_w, box_h), 2)

        ego = world_model.ego_state
        ego_peak_r = 0.0
        ego_peak_t = 0.0
        if ego:
            r_ego, c_ego = converter.world_to_grid(ego["x"], ego["y"])
            ego_peak_r = field.get_peak_risk_over_horizon(r_ego, c_ego)
            ego_peak_t = field.get_time_of_peak_risk(r_ego, c_ego)

        lines = [
            f"[FUTURE RISK FIELD — PHASE 10]",
            f"Timestep: t = +{t_val:.1f} s (Index {time_index + 1}/{len(field.risk_grids)})",
            f"Horizon Max Risk:  {field.maximum_risk:.2f} | Avg: {field.average_risk:.3f}",
            f"Ego Cell Peak Risk:{ego_peak_r:.2f} (Time: t = +{ego_peak_t:.1f} s)",
            f"Active Track Sources: {len(field.active_tracks)} actors",
            f"Controls: [LEFT/RIGHT] Change Future Timestep",
        ]

        for i, line in enumerate(lines):
            c = (195, 100, 255) if i == 0 else ((255, 215, 0) if i == 1 else ((231, 76, 60) if i == 3 else (220, 235, 245)))
            txt = self.font.render(line, True, c)
            surface.blit(txt, (box_x + 10, box_y + 8 + i * 22))

    def render_safe_space(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        safe_space_map: Optional[Any] = None,
        planning_result: Optional[Any] = None,
    ):
        """
        Renders Phase 11 Safe-Space / Negative-Space Planner Overlay.
        Draws negative-space drivable cells, candidate corridor centerlines, and highlights the selected path.
        """
        converter = world_model.converter
        grid = world_model.grid
        ppm = converter.ppm
        grid_res = converter.grid_res
        cell_px = max(1, int(grid_res * ppm))

        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        # 1. Render Drivable Safe-Space & Clearance Overlay
        clearance_grid = safe_space_map.clearance_grid if safe_space_map is not None else None

        if clearance_grid is not None:
            for r in range(grid.num_rows):
                for c in range(grid.num_cols):
                    cell = grid.cells[r][c]
                    if not cell.is_drivable:
                        continue  # Skip non-drivable cells

                    c_val = clearance_grid[r, c]
                    px, py = converter.world_to_screen(
                        cell.x_world - grid_res / 2.0,
                        cell.y_world - grid_res / 2.0,
                        camera_x,
                        camera_y,
                    )

                    if px < -cell_px or px > surface.get_width() or py < -cell_px or py > surface.get_height():
                        continue

                    # Color coding based on clearance distance (Green: Safe/High clearance, Yellow: Moderate, Red: Tight)
                    if c_val >= 2.0:
                        color = (46, 204, 113, 35)    # Safe Green
                    elif c_val >= 1.0:
                        color = (241, 196, 15, 45)    # Moderate Yellow
                    else:
                        color = (231, 76, 60, 55)     # Tight Red

                    pygame.draw.rect(overlay, color, (px, py, cell_px, cell_px))

        surface.blit(overlay, (0, 0))

        # 2. Render Candidate Corridors & Paths
        candidates = []
        selected_corridor = None

        if planning_result is not None:
            candidates = getattr(planning_result, "candidate_paths", [])
            selected_corridor = getattr(planning_result, "selected_corridor", None)
        elif safe_space_map is not None:
            candidates = getattr(safe_space_map, "candidate_corridors", [])
            selected_corridor = getattr(safe_space_map, "selected_corridor", None)

        for cand in candidates:
            if not cand.centerline or len(cand.centerline) < 2:
                continue

            screen_pts = [
                converter.world_to_screen(wx, wy, camera_x, camera_y)
                for wx, wy in cand.centerline
            ]

            is_selected = (selected_corridor is not None and cand.corridor_id == selected_corridor.corridor_id)

            if is_selected:
                # Highlight Selected Safe Path (Thick Cyan / Bright Green)
                path_color = (0, 240, 220)
                path_width = 5
            elif cand.is_valid:
                # Valid Candidate Path (Dashed Orange / Yellow)
                path_color = (241, 196, 15)
                path_width = 2
            else:
                # Rejected / Invalid Candidate Path (Red)
                path_color = (200, 50, 50)
                path_width = 1

            if len(screen_pts) >= 2:
                pygame.draw.lines(surface, path_color, False, screen_pts, path_width)

            # Candidate ID Label above starting segment
            start_px, start_py = screen_pts[0]
            lbl_str = f"{cand.corridor_id} ({cand.name}) | Score: {cand.total_score:.2f}"
            if not cand.is_valid:
                lbl_str += f" [REJECTED]"

            txt = self.font.render(lbl_str, True, path_color)
            lbl_bg = pygame.Surface((txt.get_width() + 6, txt.get_height() + 2), pygame.SRCALPHA)
            lbl_bg.fill((10, 20, 30, 200))
            surface.blit(lbl_bg, (start_px - 3, start_py - 18))
            surface.blit(txt, (start_px, start_py - 17))

    def render_candidate_debug_panel(
        self,
        surface: pygame.Surface,
        planning_result: Optional[Any],
    ):
        """
        Renders Candidate Scorer Telemetry HUD Debug Panel.
        """
        if planning_result is None:
            return

        candidates = getattr(planning_result, "candidate_paths", [])
        reason = getattr(planning_result, "reason", "N/A")
        selected_corridor = getattr(planning_result, "selected_corridor", None)

        panel_w = 420
        panel_h = max(160, 45 + len(candidates) * 45)
        panel_x = 20
        panel_y = surface.get_height() - panel_h - 20

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((12, 28, 38, 235))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (0, 240, 220), (panel_x, panel_y, panel_w, panel_h), 2)

        header = f"[SAFE-SPACE PLANNER — PHASE 11 | {reason}]"
        txt_hdr = self.font.render(header, True, (0, 240, 220))
        surface.blit(txt_hdr, (panel_x + 10, panel_y + 8))

        curr_y = panel_y + 30

        for idx, cand in enumerate(candidates[:4]):
            is_sel = (selected_corridor is not None and cand.corridor_id == selected_corridor.corridor_id)
            c_tag = " >>> SELECTED <<<" if is_sel else (" [INVALID]" if not cand.is_valid else "")
            c_color = (0, 255, 200) if is_sel else ((241, 196, 15) if cand.is_valid else (220, 80, 80))

            line1 = f"{cand.corridor_id} ({cand.name}): Len={cand.length:.1f}m | Score={cand.total_score:.2f}{c_tag}"
            line2 = f"  Risk={cand.avg_risk:.2f} | PeakR={cand.peak_risk:.2f} | MinClr={cand.min_clearance:.1f}m | Surf={cand.surface_cost:.2f}"

            t1 = self.font.render(line1, True, c_color)
            t2 = self.font.render(line2, True, (200, 215, 225))
            surface.blit(t1, (panel_x + 10, curr_y))
            surface.blit(t2, (panel_x + 10, curr_y + 17))
            curr_y += 38

    def render_replanning_overlay(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        replanning_manager: Any,
        camera_x: float,
        camera_y: float,
    ):
        """
        Renders Phase 12 Adaptive Replanning Visual Overlay (previous path dashed, active path solid,
        trigger locations, and SAFETY_HOLD banners).
        """
        if replanning_manager is None:
            return

        converter = world_model.converter
        state = replanning_manager.current_path_state

        # 1. Render Previous Path (Dashed Orange/Red Line)
        prev_path = replanning_manager.previous_path
        if prev_path is not None and prev_path.world_points:
            prev_screen_pts = [
                converter.world_to_screen(wx, wy, camera_x, camera_y)
                for wx, wy in prev_path.world_points
            ]
            if len(prev_screen_pts) >= 2:
                # Draw dashed line segment representation
                for i in range(0, len(prev_screen_pts) - 1, 2):
                    p1 = prev_screen_pts[i]
                    p2 = prev_screen_pts[min(i + 1, len(prev_screen_pts) - 1)]
                    pygame.draw.line(surface, (255, 140, 0), p1, p2, 2)

        # 2. Render Active Path State
        if state.path is not None and state.path.world_points:
            active_screen_pts = [
                converter.world_to_screen(wx, wy, camera_x, camera_y)
                for wx, wy in state.path.world_points[state.current_waypoint_index:]
            ]
            if len(active_screen_pts) >= 2:
                path_color = (0, 240, 220) if state.path_valid else (240, 50, 50)
                pygame.draw.lines(surface, path_color, False, active_screen_pts, 4)

        # 3. Render SAFETY_HOLD Warning Banner if active
        if replanning_manager.status.name == "SAFETY_HOLD":
            banner_w, banner_h = 560, 45
            banner_x = (surface.get_width() - banner_w) // 2
            banner_y = 15

            b_surf = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
            b_surf.fill((200, 30, 30, 230))
            surface.blit(b_surf, (banner_x, banner_y))
            pygame.draw.rect(surface, (255, 255, 255), (banner_x, banner_y, banner_w, banner_h), 2)

            warn_txt = self.font.render("🚨 SAFETY HOLD: NO SAFE CORRIDOR FOUND — VEHICLE HALTED", True, (255, 255, 255))
            surface.blit(warn_txt, (banner_x + 15, banner_y + 13))

    def render_replanning_hud(
        self,
        surface: pygame.Surface,
        replanning_manager: Any,
    ):
        """
        Renders Phase 12 Replanning Telemetry HUD & Event Log Panel.
        """
        if replanning_manager is None:
            return

        state = replanning_manager.current_path_state
        metrics = replanning_manager.metrics
        last_decision = replanning_manager.last_decision
        events = replanning_manager.event_log

        panel_w = 460
        panel_h = 240
        panel_x = surface.get_width() - panel_w - 20
        panel_y = 70

        hud_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        hud_bg.fill((10, 22, 34, 235))
        surface.blit(hud_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (58, 134, 255), (panel_x, panel_y, panel_w, panel_h), 2)

        reason_str = last_decision.reason.name if last_decision else "NO_REPLAN_REQUIRED"
        status_str = replanning_manager.status.name

        status_color = (46, 204, 113) if status_str == "FOLLOWING_PATH" else ((241, 196, 15) if status_str == "PLANNING" else (231, 76, 60))

        header = f"[PHASE 12: ADAPTIVE REPLANNER | {status_str}]"
        txt_hdr = self.font.render(header, True, status_color)
        surface.blit(txt_hdr, (panel_x + 12, panel_y + 8))

        lines = [
            f"Active Path: {state.path_id} (Reason: {state.reason_for_creation})",
            f"Last Trigger: {reason_str} | Mode: {replanning_manager.mode}",
            f"Peak Future Risk: {state.current_peak_risk:.2f} | Avg Risk: {state.current_average_risk:.2f}",
            f"Min Clearance: {state.minimum_clearance:.1f}m | Deviation: {state.path_deviation:.1f}m",
            f"Replans: Total={metrics.total_replans} (Hard={metrics.hard_trigger_replans}, Soft={metrics.soft_trigger_replans}, Unnecessary={metrics.unnecessary_replans})",
            f"Latency: Last={metrics.last_latency_ms:.1f}ms | Avg={metrics.avg_latency_ms:.1f}ms",
            f"Safety Holds: {metrics.safety_holds} | Failed Replans: {metrics.failed_replans}",
        ]

        for i, line in enumerate(lines):
            t = self.font.render(line, True, (220, 230, 240))
            surface.blit(t, (panel_x + 12, panel_y + 30 + i * 18))

        # Render Log History Section
        pygame.draw.line(surface, (58, 134, 255), (panel_x + 10, panel_y + 160), (panel_x + panel_w - 10, panel_y + 160), 1)
        log_hdr = self.font.render("Recent Replan Event History:", True, (255, 215, 0))
        surface.blit(log_hdr, (panel_x + 12, panel_y + 165))

        recent_events = events[-3:] if events else []
        if not recent_events:
            no_evt = self.font.render("  (No replan events recorded)", True, (150, 160, 170))
            surface.blit(no_evt, (panel_x + 12, panel_y + 185))
        else:
            for idx, evt in enumerate(recent_events):
                trig_tag = "HARD" if evt.is_hard_trigger else "SOFT"
                e_line = f"  [{evt.event_id}] t={evt.timestamp:.1f}s | {evt.reason.name} ({trig_tag}) | {evt.latency_ms:.1f}ms"
                e_txt = self.font.render(e_line, True, (180, 220, 255))
                surface.blit(e_txt, (panel_x + 12, panel_y + 185 + idx * 17))

    def render_control_debug(
        self,
        surface: pygame.Surface,
        world_model: WorldModel,
        camera_x: float,
        camera_y: float,
        vehicle_controller: Any = None,
    ):
        """
        Renders Phase 13 Decision & Vehicle Control Overlay and Telemetry HUD Panel.
        """
        converter = world_model.converter
        ego = world_model.ego_state
        def_start = converter.sim_to_world(5.0, 0.0)
        wx, wy = ego.get("x", def_start[0]), ego.get("y", def_start[1])
        heading = ego.get("heading", 0.0)
        curr_speed = ego.get("velocity", 0.0)

        cmd = getattr(vehicle_controller, "last_command", None) if vehicle_controller else None

        # 1. Render Lookahead Target Point on Canvas if available
        if cmd is not None and cmd.lookahead_point is not None:
            lx, ly = cmd.lookahead_point
            l_px, l_py = converter.world_to_screen(lx, ly, camera_x, camera_y)

            # Draw Lookahead Target Indicator (Magenta/Cyan Circle & Crosshair)
            pygame.draw.circle(surface, (255, 0, 220), (l_px, l_py), 8, 2)
            pygame.draw.circle(surface, (0, 255, 230), (l_px, l_py), 3)
            pygame.draw.line(surface, (255, 0, 220), (l_px - 10, l_py), (l_px + 10, l_py), 1)
            pygame.draw.line(surface, (255, 0, 220), (l_px, l_py - 10), (l_px, l_py + 10), 1)

            # Lookahead label
            lbl = self.font.render(f"PurePursuit Ld ({lx:.1f}m, {ly:.1f}m)", True, (255, 100, 240))
            surface.blit(lbl, (l_px + 12, l_py - 10))

        # 2. Render Vehicle Heading & Steering Vector
        px, py = converter.world_to_screen(wx, wy, camera_x, camera_y)
        steer_angle = cmd.steering_angle if cmd else 0.0
        steer_vec_len = 30
        end_x = px + int(steer_vec_len * math.cos(heading + steer_angle))
        end_y = py - int(steer_vec_len * math.sin(heading + steer_angle))
        pygame.draw.line(surface, (255, 255, 0), (px, py), (end_x, end_y), 3)

        # 3. Decision & Vehicle Control Telemetry Panel (Top Left / Overlay)
        panel_w, panel_h = 320, 210
        panel_x = 20
        panel_y = 60

        p_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        p_bg.fill((10, 20, 32, 235))
        surface.blit(p_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (255, 180, 0), (panel_x, panel_y, panel_w, panel_h), 2)

        dec_state_str = cmd.decision_result.state_name if cmd else "NORMAL_DRIVING"
        target_kmh = cmd.target_speed_kmh if cmd else (curr_speed * 3.6)
        curr_kmh = curr_speed * 3.6
        steer_deg = math.degrees(steer_angle)

        # Extract risk and clearance metrics from world model
        peak_risk = 0.0
        min_clearance = 999.0
        if hasattr(world_model, "planning_result") and world_model.planning_result and world_model.planning_result.selected_corridor:
            peak_risk = world_model.planning_result.selected_corridor.peak_risk
            min_clearance = world_model.planning_result.selected_corridor.min_clearance

        state_color = (46, 204, 113) if dec_state_str == "NORMAL_DRIVING" else ((241, 196, 15) if dec_state_str in ("CAUTION", "SLOW_DOWN", "REPLAN") else (231, 76, 60))

        hdr = self.font.render(f"[DECISION & VEHICLE CONTROL]", True, (255, 200, 0))
        surface.blit(hdr, (panel_x + 12, panel_y + 8))

        lines = [
            f"Decision:   {dec_state_str}",
            f"Speed:      {int(round(curr_kmh))} km/h ({curr_speed:.1f} m/s)",
            f"Target:     {int(round(target_kmh))} km/h ({cmd.target_speed if cmd else 0.0:.1f} m/s)",
            f"Steering:   {steer_deg:+.1f}° ({'R' if steer_deg > 0 else 'L' if steer_deg < 0 else '0'})",
            f"Risk:       {peak_risk:.2f}",
            f"Clearance:  {min_clearance:.1f} m",
            f"Controller: {cmd.controller_type if cmd else 'PURE_PURSUIT'}",
            f"Braking:    {cmd.braking_state if cmd else 'CRUISING'}",
        ]

        for idx, line in enumerate(lines):
            c = state_color if idx == 0 else (220, 235, 245)
            txt = self.font.render(line, True, c)
            surface.blit(txt, (panel_x + 12, panel_y + 28 + idx * 21))

    def render_scenario_hud(
        self,
        surface: pygame.Surface,
        scenario_runner: Any,
    ):
        """
        Renders Phase 14 Scenario Framework HUD Panel.
        """
        if scenario_runner is None or scenario_runner.current_scenario is None:
            return

        sc = scenario_runner.current_scenario
        m = scenario_runner.metrics

        panel_w, panel_h = 440, 190
        panel_x = surface.get_width() - panel_w - 20
        panel_y = surface.get_height() - panel_h - 40

        s_bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        s_bg.fill((15, 25, 38, 235))
        surface.blit(s_bg, (panel_x, panel_y))
        pygame.draw.rect(surface, (155, 89, 182), (panel_x, panel_y, panel_w, panel_h), 2)

        hdr = self.font.render(f"[PHASE 14: SCENARIO FRAMEWORK — {sc.name.upper()}]", True, (210, 140, 255))
        surface.blit(hdr, (panel_x + 12, panel_y + 8))

        road_str = sc.road_type.value if hasattr(sc.road_type, "value") else str(sc.road_type)
        diff_str = sc.difficulty.value if hasattr(sc.difficulty, "value") else str(sc.difficulty)

        lines = [
            f"Scenario ID: {sc.scenario_id} | Seed: {sc.seed} | Road: {road_str}",
            f"Difficulty:  {diff_str} | Duration: {m.total_travel_time:.1f}s / {sc.duration:.1f}s",
            f"Metrics:     Collisions={m.collision_occurred} | Near Misses={m.near_collision_count} | Replans={m.replan_count}",
            f"Clearance:   Min={m.min_clearance:.1f}m | Risk Peak={m.max_future_risk:.2f} | Uncert={m.max_uncertainty:.2f}",
        ]

        for idx, line in enumerate(lines):
            txt = self.font.render(line, True, (220, 230, 245))
            surface.blit(txt, (panel_x + 12, panel_y + 30 + idx * 18))

        # Render Expected Checkpoints Status
        pygame.draw.line(surface, (155, 89, 182), (panel_x + 10, panel_y + 110), (panel_x + panel_w - 10, panel_y + 110), 1)
        chk_hdr = self.font.render("Expected Evaluation Checkpoints:", True, (255, 215, 0))
        surface.blit(chk_hdr, (panel_x + 12, panel_y + 115))

        if not sc.expected_events:
            no_chk = self.font.render("  (Standard baseline scenario)", True, (160, 170, 185))
            surface.blit(no_chk, (panel_x + 12, panel_y + 135))
        else:
            for idx, ee in enumerate(sc.expected_events[:3]):
                st_icon = "✔ TRIGGERED" if ee.triggered else "⏳ PENDING"
                c_icon = (46, 204, 113) if ee.triggered else (241, 196, 15)
                e_str = f"  [{ee.event_id}] {ee.description[:26]}... {st_icon}"
                e_txt = self.font.render(e_str, True, c_icon)
                surface.blit(e_txt, (panel_x + 12, panel_y + 135 + idx * 17))










