"""Shared colours, fonts and drawing helpers for the desktop interface."""

from pathlib import Path

import pygame


WIDTH = 1280
HEIGHT = 820
FPS = 60

BG = (8, 13, 27)
PANEL = (15, 24, 45)
PANEL_2 = (20, 32, 59)
GRID = (55, 80, 122)
GRID_BRIGHT = (88, 163, 232)
TEXT = (232, 242, 255)
MUTED = (143, 166, 199)
CYAN = (55, 220, 255)
PURPLE = (154, 112, 255)
GREEN = (82, 232, 164)
RED = (255, 94, 130)
YELLOW = (255, 206, 92)
FONT_FILES = (
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
)


def make_font(size, bold=False):
    for path in FONT_FILES:
        if path.exists():
            try:
                font = pygame.font.Font(str(path), size)
                font.set_bold(bold)
                return font
            except (pygame.error, OSError):
                continue
    for name in ("Microsoft YaHei", "Segoe UI", "Arial"):
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except (pygame.error, TypeError, OSError):
            continue
    return pygame.font.Font(None, size)


def text(surface, value, position, size=20, color=TEXT, bold=False, anchor="topleft"):
    image = make_font(size, bold).render(str(value), True, color)
    rect = image.get_rect()
    setattr(rect, anchor, position)
    surface.blit(image, rect)
    return rect


def panel(surface, rect, colour=PANEL, border=GRID, radius=18):
    pygame.draw.rect(surface, colour, rect, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)


def button(surface, rect, label, active=False, hovered=False, accent=CYAN, small=False):
    fill = (28, 48, 82) if not active else (24, 86, 116)
    if hovered:
        fill = (35, 70, 112) if not active else (30, 112, 145)
    pygame.draw.rect(surface, fill, rect, border_radius=12)
    pygame.draw.rect(surface, accent if active else GRID, rect, width=2, border_radius=12)
    text(surface, label, rect.center, 17 if small else 19, TEXT, bold=active, anchor="center")


def divider(surface, x1, y1, x2, y2, colour=GRID):
    pygame.draw.line(surface, colour, (x1, y1), (x2, y2), 1)
