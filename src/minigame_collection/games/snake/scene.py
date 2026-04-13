from __future__ import annotations

import math
from enum import Enum

import pygame

from ...config import APP_CONFIG
from ...scene import SceneCommand, ShowMenu
from ...scores import LEADERBOARD_LIMIT, LeaderboardStore, ScoreEntry
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
CARD_BACKGROUND = (17, 29, 46)
INPUT_BACKGROUND = (12, 24, 40)

SNAKE_GAME_ID = "snake"
NICKNAME_MAX_LENGTH = 8
ALLOWED_NICKNAME_CHARS = {" ", "-", "_"}


def speed_interval_for_score(score: int) -> float:
    step = 0.16 - min(score // 4, 8) * 0.01
    return max(0.08, step)


class SnakeSceneMode(Enum):
    PLAYING = "playing"
    ENTERING_NAME = "entering_name"
    GAME_OVER_RESULTS = "game_over_results"


class SnakeScene:
    def __init__(
        self,
        score_store: LeaderboardStore,
        *,
        game_id: str = SNAKE_GAME_ID,
    ) -> None:
        self._score_store = score_store
        self._game_id = game_id
        self._game = SnakeGame(APP_CONFIG.grid_columns, APP_CONFIG.grid_rows)
        self._mode = SnakeSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._elapsed = 0.0
        self._nickname = ""
        self._leaderboard: list[ScoreEntry] = []
        self._status_message: str | None = None
        self._title_font = pygame.font.Font(None, 60)
        self._hud_font = pygame.font.Font(None, 34)
        self._meta_font = pygame.font.Font(None, 26)
        self._overlay_title_font = pygame.font.Font(None, 68)
        self._overlay_font = pygame.font.Font(None, 32)
        self._leaderboard_title_font = pygame.font.Font(None, 34)
        self._leaderboard_font = pygame.font.Font(None, 30)
        self._input_font = pygame.font.Font(None, 38)
        self._status_font = pygame.font.Font(None, 28)

    @property
    def mode(self) -> SnakeSceneMode:
        return self._mode

    @property
    def leaderboard(self) -> tuple[ScoreEntry, ...]:
        return tuple(self._leaderboard)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type != pygame.KEYDOWN:
            return None

        if self._mode is SnakeSceneMode.PLAYING:
            return self._handle_playing_event(event)
        if self._mode is SnakeSceneMode.ENTERING_NAME:
            return self._handle_name_entry_event(event)
        return self._handle_results_event(event)

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        if self._mode is not SnakeSceneMode.PLAYING:
            return None
        if not self._game.state.alive:
            self._begin_post_game_flow()
            return None

        self._step_accumulator += delta_seconds
        interval = speed_interval_for_score(self._game.state.score)
        while self._step_accumulator >= interval and self._game.state.alive:
            self._step_accumulator -= interval
            self._game.step()
            interval = speed_interval_for_score(self._game.state.score)

        if not self._game.state.alive:
            self._begin_post_game_flow()
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_backdrop(surface)
        self._draw_hud(surface)
        self._draw_playfield(surface)
        if self._mode is not SnakeSceneMode.PLAYING:
            self._draw_game_over_overlay(surface)

    def _handle_playing_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            return ShowMenu()

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

    def _handle_name_entry_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            self._nickname = ""
            self._show_results()
            return None
        if event.key == pygame.K_BACKSPACE:
            self._nickname = self._nickname[:-1]
            return None
        if event.key == pygame.K_RETURN:
            self._save_entered_score()
            return None

        if len(self._nickname) >= NICKNAME_MAX_LENGTH:
            return None

        candidate = event.unicode
        if len(candidate) == 1 and self._is_allowed_nickname_character(candidate):
            self._nickname += candidate
        return None

    def _handle_results_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            return ShowMenu()
        if event.key == pygame.K_RETURN:
            self._restart_game()
        return None

    def _begin_post_game_flow(self) -> None:
        self._refresh_leaderboard()
        self._status_message = None
        if self._should_prompt_for_name():
            self._mode = SnakeSceneMode.ENTERING_NAME
            self._nickname = ""
            return
        self._show_results()

    def _should_prompt_for_name(self) -> bool:
        score = self._game.state.score
        if not self._score_store.available or score <= 0:
            return False
        return self._score_store.qualifies(self._game_id, score, limit=LEADERBOARD_LIMIT)

    def _save_entered_score(self) -> None:
        nickname = self._nickname.strip()
        if not nickname:
            return

        saved = self._score_store.save_score(self._game_id, nickname, self._game.state.score)
        self._nickname = ""
        if saved:
            self._show_results("Score saved.")
            return
        self._show_results("Scores unavailable for this run.")

    def _show_results(self, message: str | None = None) -> None:
        self._refresh_leaderboard()
        self._mode = SnakeSceneMode.GAME_OVER_RESULTS
        if message is not None:
            self._status_message = message
            return
        if not self._score_store.available:
            self._status_message = "Scores unavailable for this run."
        else:
            self._status_message = None

    def _refresh_leaderboard(self) -> None:
        self._leaderboard = self._score_store.top_scores(
            self._game_id,
            limit=LEADERBOARD_LIMIT,
        )

    def _restart_game(self) -> None:
        self._game.reset()
        self._mode = SnakeSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._nickname = ""
        self._leaderboard = []
        self._status_message = None

    def _is_allowed_nickname_character(self, character: str) -> bool:
        return character.isascii() and (
            character.isalnum() or character in ALLOWED_NICKNAME_CHARS
        )

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

        card_rect = pygame.Rect(88, 120, 576, 448)
        pygame.draw.rect(surface, CARD_BACKGROUND, card_rect, border_radius=28)
        pygame.draw.rect(surface, ACCENT_SOFT, card_rect, width=2, border_radius=28)

        title = self._overlay_title_font.render("Game Over", True, TEXT_MAIN)
        score = self._overlay_font.render(
            f"Final score: {self._game.state.score}",
            True,
            TEXT_MAIN,
        )
        surface.blit(title, title.get_rect(center=(card_rect.centerx, card_rect.y + 52)))
        surface.blit(score, score.get_rect(center=(card_rect.centerx, card_rect.y + 104)))

        if self._mode is SnakeSceneMode.ENTERING_NAME:
            self._draw_name_entry(surface, card_rect)
        else:
            self._draw_results(surface, card_rect)

    def _draw_name_entry(self, surface: pygame.Surface, card_rect: pygame.Rect) -> None:
        prompt_text = "New high score! Enter a nickname"
        prompt_font = fit_font(
            prompt_text,
            max_width=card_rect.width - 56,
            starting_size=32,
            min_size=24,
        )
        prompt = prompt_font.render(prompt_text, True, ACCENT_SOFT)
        surface.blit(prompt, prompt.get_rect(center=(card_rect.centerx, card_rect.y + 170)))

        input_rect = pygame.Rect(card_rect.x + 96, card_rect.y + 214, card_rect.width - 192, 62)
        pygame.draw.rect(surface, INPUT_BACKGROUND, input_rect, border_radius=16)
        pygame.draw.rect(surface, ACCENT, input_rect, width=2, border_radius=16)

        nickname = self._nickname or "Type up to 8 chars"
        nickname_color = TEXT_MAIN if self._nickname else TEXT_MUTED
        nickname_surface = self._input_font.render(nickname, True, nickname_color)
        surface.blit(nickname_surface, (input_rect.x + 16, input_rect.y + 11))

        if self._nickname and int(self._elapsed * 2.4) % 2 == 0:
            cursor_x = input_rect.x + 18 + nickname_surface.get_width()
            pygame.draw.line(
                surface,
                ACCENT_SOFT,
                (cursor_x, input_rect.y + 12),
                (cursor_x, input_rect.bottom - 12),
                2,
            )

        details_text = "Letters, numbers, space, - and _"
        details_font = fit_font(
            details_text,
            max_width=card_rect.width - 64,
            starting_size=24,
            min_size=18,
        )
        details = details_font.render(details_text, True, TEXT_MUTED)
        surface.blit(details, details.get_rect(center=(card_rect.centerx, card_rect.y + 314)))

        hint_text = "Enter to save   •   Esc to skip"
        hint_font = fit_font(
            hint_text,
            max_width=card_rect.width - 64,
            starting_size=28,
            min_size=20,
        )
        hint = hint_font.render(hint_text, True, TEXT_MUTED)
        surface.blit(hint, hint.get_rect(center=(card_rect.centerx, card_rect.y + 368)))

    def _draw_results(self, surface: pygame.Surface, card_rect: pygame.Rect) -> None:
        prompt_text = "Press Enter to restart or Esc to return to menu"
        prompt_font = fit_font(
            prompt_text,
            max_width=card_rect.width - 64,
            starting_size=28,
            min_size=20,
        )
        prompt_lines = wrap_text(prompt_text, prompt_font, card_rect.width - 64)
        prompt_top = card_rect.y + 142
        line_height = prompt_font.get_linesize()
        for index, line in enumerate(prompt_lines):
            prompt = prompt_font.render(line, True, TEXT_MUTED)
            surface.blit(
                prompt,
                prompt.get_rect(center=(card_rect.centerx, prompt_top + index * line_height)),
            )

        leaderboard_top = card_rect.y + 214
        if self._status_message is not None:
            status = self._status_font.render(
                self._status_message,
                True,
                self._status_color(self._status_message),
            )
            surface.blit(status, status.get_rect(center=(card_rect.centerx, card_rect.y + 190)))
            leaderboard_top += 22

        self._draw_leaderboard(surface, card_rect, top=leaderboard_top)

    def _draw_leaderboard(
        self,
        surface: pygame.Surface,
        card_rect: pygame.Rect,
        *,
        top: int,
    ) -> None:
        title = self._leaderboard_title_font.render("Top 5 Scores", True, TEXT_MAIN)
        surface.blit(title, title.get_rect(center=(card_rect.centerx, top)))

        if not self._leaderboard:
            empty = self._leaderboard_font.render("No saved scores yet.", True, TEXT_MUTED)
            surface.blit(empty, empty.get_rect(center=(card_rect.centerx, top + 46)))
            return

        start_y = top + 38
        line_height = 32
        rank_x = card_rect.x + 70
        name_x = card_rect.x + 130
        score_x = card_rect.right - 70
        for index, entry in enumerate(self._leaderboard, start=1):
            y = start_y + (index - 1) * line_height
            rank = self._leaderboard_font.render(f"{index:02d}", True, ACCENT_SOFT)
            name = self._leaderboard_font.render(entry.player_name, True, TEXT_MAIN)
            score = self._leaderboard_font.render(str(entry.score), True, TEXT_MAIN)
            surface.blit(rank, (rank_x, y))
            surface.blit(name, (name_x, y))
            surface.blit(score, score.get_rect(topright=(score_x, y)))

    def _status_color(self, message: str) -> tuple[int, int, int]:
        if "unavailable" in message.lower():
            return FOOD
        return SNAKE_HEAD

    def _cell_rect(self, point: Point) -> pygame.Rect:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        return pygame.Rect(
            origin_x + point.x * APP_CONFIG.cell_size,
            origin_y + point.y * APP_CONFIG.cell_size,
            APP_CONFIG.cell_size,
            APP_CONFIG.cell_size,
        )


def create_snake_scene(score_store: LeaderboardStore) -> SnakeScene:
    return SnakeScene(score_store)
