"""
IRIS Dashboard Base Panels & UI Utilities (Combined Phase 15).
Provides reusable UI panel layout containers, card boxes, text formatters, and drawing utilities for Pygame.
"""

import pygame
from typing import Tuple, List, Optional, Dict, Any

# Dark Theme Color Palette
COLOR_BG = (15, 23, 42)          # Deep Slate #0f172a
COLOR_PANEL_BG = (30, 41, 59)    # Dark Blue-Gray #1e293b
COLOR_BORDER = (51, 65, 85)      # Slate Border #334155
COLOR_TEXT_PRIMARY = (248, 250, 252)  # Bright White
COLOR_TEXT_MUTED = (148, 163, 184)    # Slate Gray
COLOR_ACCENT = (59, 130, 246)          # Vibrant Blue
COLOR_SUCCESS = (34, 197, 94)          # Bright Green
COLOR_WARNING = (234, 179, 8)          # Bright Yellow
COLOR_DANGER = (239, 68, 68)           # Bright Red
COLOR_CYAN = (6, 182, 212)             # Bright Cyan


class BasePanel:
    """Base class for dashboard telemetry panels."""

    def __init__(self, title: str, rect: Tuple[int, int, int, int]):
        self.title = title
        self.rect = pygame.Rect(rect)
        self.font_title = None
        self.font_body = None
        self._init_fonts()

    def _init_fonts(self):
        if not pygame.font.get_init():
            pygame.font.init()
        self.font_title = pygame.font.SysFont("Arial", 16, bold=True)
        self.font_body = pygame.font.SysFont("Consolas", 13)

    def draw_background(self, surface: pygame.Surface):
        """Render panel container background and border header."""
        pygame.draw.rect(surface, COLOR_PANEL_BG, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_BORDER, self.rect, width=1, border_radius=8)

        # Header bar
        header_rect = pygame.Rect(self.rect.x, self.rect.y, self.rect.width, 32)
        pygame.draw.rect(surface, (47, 63, 86), header_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, COLOR_BORDER, (self.rect.x, self.rect.y + 32), (self.rect.x + self.rect.width, self.rect.y + 32), 1)

        title_lbl = self.font_title.render(self.title, True, COLOR_TEXT_PRIMARY)
        surface.blit(title_lbl, (self.rect.x + 12, self.rect.y + 6))

    def render_kv_pair(self, surface: pygame.Surface, key: str, value: str, x: int, y: int,
                       val_color: Tuple[int, int, int] = COLOR_TEXT_PRIMARY):
        """Render key-value pair text row."""
        k_txt = self.font_body.render(f"{key}:", True, COLOR_TEXT_MUTED)
        v_txt = self.font_body.render(str(value), True, val_color)
        surface.blit(k_txt, (x, y))
        surface.blit(v_txt, (x + 130, y))
