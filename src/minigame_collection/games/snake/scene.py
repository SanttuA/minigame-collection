from __future__ import annotations

import math

import pygame

from ...config import APP_CONFIG
from ...scene import SceneCommand, ShowMenu
from ...ui import fit_font, wrap_text
from .logic import Direction, Point, SnakeGame

BACKGROUND = (8, 15, 28)
ACCENT = (47, 128, 237)
ACCENT_SOFT = (87, 170, 255)
PLAYFIELD = (14, 28, 46)
GRID_LINE = (28, 45, 71)
HUD_PANEL = (18, 33, 56)
TEXT_MAIN = (239, 246, 255)
TEXT_MUTED = (155, 178, 209)
SNAKE_HEAD = (99, 233, 153)
SNAKE_BODY = (49, 178, 116)
FOOD = (255, 104, 107)
OVERLAY = (7, 13, 24)


def speed_interval_for_score(score: int) -> float:
    step = 0.16 - min(score // 4, 8) * 0.01
    return max(0.08, step)


class SnakeScene:
    def __init__(self) -> None:
        self._game = SnakeGame(APP_CONFIG.grid_columns, APP_CONFIG.grid_rows)
        self._step_accumulator = 0.0
        self._elapsed = 0.0
        self._title_font = pygame.font.Font(None, 60)
        self._hud_font = pygame.font.Font(None, 34)
        self._meta_font = pygame.font.Font(None, 26)
        self._overlay_title_font = pygame.font.Font(None, 72)
        self._overlay_font = pygame.font.Font(None, 34)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key == pygame.K_ESCAPE:
            return ShowMenu()

        if not self._game.state.alive and event.key == pygame.K_RETURN:
            self._game.reset()
            self._step_accumulator = 0.0
            return None

        direction_by_key = {
            pygame.K_UP: Direction.UP,
            pygame.K_w: Direction.UP,
            pygame.K_DOWN: Direction.DOWN,
            pygame.K_s: Direction.DOWN,
            pygame.K_LEFT: Direction.LEFT,
            pygame.K_a: Direction.LEFT,
            pygame.K_RIGHT: Direction.RIGHT,
            pygame.K_d: Direction.RIGHT,
        }
        direction = direction_by_key.get(event.key)
        if direction is not None:
            self._game.request_direction(direction)
        return None

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        if not self._game.state.alive:
            return None

        self._step_accumulator += delta_seconds
        interval = speed_interval_for_score(self._game.state.score)
        while self._step_accumulator >= interval and self._game.state.alive:
            self._step_accumulator -= interval
            self._game.step()
            interval = speed_interval_for_score(self._game.state.score)
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_backdrop(surface)
        self._draw_hud(surface)
        self._draw_playfield(surface)
        if not self._game.state.alive:
            self._draw_game_over_overlay(surface)

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(self._elapsed * 1.8) + 1.0) / 2.0
        orbit_x = int(APP_CONFIG.window_width * (0.72 + pulse * 0.08))
        orbit_y = int(APP_CONFIG.window_height * (0.18 + pulse * 0.04))
        pygame.draw.circle(surface, (19, 52, 93), (orbit_x, orbit_y), 130)
        pygame.draw.circle(surface, (13, 36, 65), (110, 110), 90)
        pygame.draw.rect(surface, (11, 22, 40), (0, 96, APP_CONFIG.window_width, 8))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(16, 16, APP_CONFIG.window_width - 32, 92)
        pygame.draw.rect(surface, HUD_PANEL, panel_rect, border_radius=24)
        pygame.draw.rect(surface, ACCENT, panel_rect, width=2, border_radius=24)

        title = self._title_font.render("Snake", True, TEXT_MAIN)
        score = self._hud_font.render(
            f"Score {self._game.state.score:02d}",
            True,
            TEXT_MAIN,
        )
        controls_text = "Arrows / WASD to move   •   Esc to menu"
        controls_font = fit_font(
            controls_text,
            max_width=panel_rect.width - 288,
            starting_size=26,
            min_size=18,
        )
        controls = controls_font.render(controls_text, True, TEXT_MUTED)
        speed = self._meta_font.render(
            f"Step {speed_interval_for_score(self._game.state.score):.2f}s",
            True,
            ACCENT_SOFT,
        )

        surface.blit(title, (34, 26))
        surface.blit(score, (34, 66))
        surface.blit(controls, (260, 34))
        surface.blit(speed, (260, 68))

    def _draw_playfield(self, surface: pygame.Surface) -> None:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        width, height = APP_CONFIG.playfield_size
        playfield = pygame.Rect(origin_x, origin_y, width, height)
        pygame.draw.rect(surface, PLAYFIELD, playfield, border_radius=18)
        pygame.draw.rect(surface, ACCENT, playfield, width=2, border_radius=18)

        for column in range(1, APP_CONFIG.grid_columns):
            x = origin_x + column * APP_CONFIG.cell_size
            pygame.draw.line(
                surface,
                GRID_LINE,
                (x, origin_y),
                (x, origin_y + height),
                1,
            )
        for row in range(1, APP_CONFIG.grid_rows):
            y = origin_y + row * APP_CONFIG.cell_size
            pygame.draw.line(
                surface,
                GRID_LINE,
                (origin_x, y),
                (origin_x + width, y),
                1,
            )

        food = self._game.state.food
        if food is not None:
            food_rect = self._cell_rect(food).inflate(-12, -12)
            pygame.draw.ellipse(surface, FOOD, food_rect)

        for index, segment in enumerate(reversed(self._game.state.body)):
            rect = self._cell_rect(segment).inflate(-6, -6)
            color = SNAKE_HEAD if index == len(self._game.state.body) - 1 else SNAKE_BODY
            pygame.draw.rect(surface, color, rect, border_radius=10)

    def _draw_game_over_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(APP_CONFIG.window_size, pygame.SRCALPHA)
        overlay.fill((*OVERLAY, 188))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(126, 192, 500, 236)
        pygame.draw.rect(surface, (17, 29, 46), card_rect, border_radius=28)
        pygame.draw.rect(surface, ACCENT_SOFT, card_rect, width=2, border_radius=28)

        title = self._overlay_title_font.render("Game Over", True, TEXT_MAIN)
        score = self._overlay_font.render(
            f"Final score: {self._game.state.score}",
            True,
            TEXT_MAIN,
        )
        prompt_text = "Press Enter to restart or Esc to return to menu"
        prompt_font = fit_font(
            prompt_text,
            max_width=card_rect.width - 64,
            starting_size=34,
            min_size=24,
        )
        prompt_lines = wrap_text(prompt_text, prompt_font, card_rect.width - 64)

        surface.blit(title, title.get_rect(center=(card_rect.centerx, card_rect.y + 62)))
        surface.blit(score, score.get_rect(center=(card_rect.centerx, card_rect.y + 122)))
        prompt_top = card_rect.y + 162
        line_height = prompt_font.get_linesize()
        for index, line in enumerate(prompt_lines):
            prompt = prompt_font.render(line, True, TEXT_MUTED)
            surface.blit(
                prompt,
                prompt.get_rect(center=(card_rect.centerx, prompt_top + index * line_height)),
            )

    def _cell_rect(self, point: Point) -> pygame.Rect:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        return pygame.Rect(
            origin_x + point.x * APP_CONFIG.cell_size,
            origin_y + point.y * APP_CONFIG.cell_size,
            APP_CONFIG.cell_size,
            APP_CONFIG.cell_size,
        )


def create_snake_scene() -> SnakeScene:
    return SnakeScene()
