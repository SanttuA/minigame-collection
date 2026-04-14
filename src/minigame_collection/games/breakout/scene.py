from __future__ import annotations

import math
from enum import Enum

import pygame

from ...config import APP_CONFIG
from ...scene import SceneCommand, ShowMenu
from ...scores import LEADERBOARD_LIMIT, LeaderboardStore, ScoreEntry
from ...ui import fit_font, wrap_text
from .logic import (
    BALL_RADIUS,
    PADDLE_HEIGHT,
    PADDLE_WIDTH,
    BreakoutGame,
    BreakoutPhase,
    Vector,
)

BACKGROUND = (11, 14, 29)
ACCENT = (255, 171, 45)
ACCENT_SOFT = (255, 214, 132)
PLAYFIELD = (17, 24, 48)
HUD_PANEL = (18, 29, 56)
TEXT_MAIN = (243, 247, 255)
TEXT_MUTED = (167, 182, 212)
TEXT_STRONG = (255, 241, 211)
PADDLE = (111, 216, 255)
BALL = (255, 245, 196)
OVERLAY = (5, 10, 20)
CARD_BACKGROUND = (17, 27, 48)
INPUT_BACKGROUND = (13, 23, 42)
BRICK_COLORS = (
    (255, 108, 92),
    (255, 149, 84),
    (255, 198, 88),
    (103, 213, 118),
    (93, 170, 255),
)

BREAKOUT_GAME_ID = "breakout"
FIXED_STEP_SECONDS = 1.0 / 120.0
NICKNAME_MAX_LENGTH = 8
ALLOWED_NICKNAME_CHARS = {" ", "-", "_"}


class BreakoutSceneMode(Enum):
    PLAYING = "playing"
    ENTERING_NAME = "entering_name"
    GAME_OVER_RESULTS = "game_over_results"


class BreakoutScene:
    def __init__(
        self,
        score_store: LeaderboardStore,
        *,
        game_id: str = BREAKOUT_GAME_ID,
    ) -> None:
        width, height = APP_CONFIG.playfield_size
        self._score_store = score_store
        self._game_id = game_id
        self._game = BreakoutGame(width, height)
        self._mode = BreakoutSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._elapsed = 0.0
        self._nickname = ""
        self._leaderboard: list[ScoreEntry] = []
        self._status_message: str | None = None
        self._moving_left = False
        self._moving_right = False
        self._title_font = pygame.font.Font(None, 58)
        self._hud_font = pygame.font.Font(None, 34)
        self._meta_font = pygame.font.Font(None, 28)
        self._banner_font = pygame.font.Font(None, 32)
        self._overlay_title_font = pygame.font.Font(None, 68)
        self._overlay_font = pygame.font.Font(None, 32)
        self._leaderboard_title_font = pygame.font.Font(None, 34)
        self._leaderboard_font = pygame.font.Font(None, 30)
        self._input_font = pygame.font.Font(None, 38)
        self._status_font = pygame.font.Font(None, 28)

    @property
    def mode(self) -> BreakoutSceneMode:
        return self._mode

    @property
    def leaderboard(self) -> tuple[ScoreEntry, ...]:
        return tuple(self._leaderboard)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if self._mode is BreakoutSceneMode.PLAYING:
            return self._handle_playing_event(event)

        if event.type != pygame.KEYDOWN:
            return None
        if self._mode is BreakoutSceneMode.ENTERING_NAME:
            return self._handle_name_entry_event(event)
        return self._handle_results_event(event)

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        if self._mode is not BreakoutSceneMode.PLAYING:
            return None

        if self._game.state.phase in (BreakoutPhase.WON, BreakoutPhase.LOST):
            self._begin_post_game_flow()
            return None

        self._step_accumulator += delta_seconds
        while self._step_accumulator >= FIXED_STEP_SECONDS:
            self._step_accumulator -= FIXED_STEP_SECONDS
            self._game.step(FIXED_STEP_SECONDS)
            if self._game.state.phase in (BreakoutPhase.WON, BreakoutPhase.LOST):
                self._begin_post_game_flow()
                break
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_backdrop(surface)
        self._draw_hud(surface)
        self._draw_playfield(surface)
        if self._mode is not BreakoutSceneMode.PLAYING:
            self._draw_outcome_overlay(surface)

    def _handle_playing_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._clear_movement()
                return ShowMenu()
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._moving_left = True
                self._sync_paddle_direction()
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self._moving_right = True
                self._sync_paddle_direction()
                return None
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self._game.launch_ball()
                return None
            return None

        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._moving_left = False
                self._sync_paddle_direction()
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self._moving_right = False
                self._sync_paddle_direction()
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
        self._clear_movement()
        self._refresh_leaderboard()
        self._status_message = None
        if self._should_prompt_for_name():
            self._mode = BreakoutSceneMode.ENTERING_NAME
            self._nickname = ""
            return
        self._show_results()

    def _should_prompt_for_name(self) -> bool:
        score = self._game.state.score
        if self._game.state.phase not in (BreakoutPhase.WON, BreakoutPhase.LOST):
            return False
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
        self._mode = BreakoutSceneMode.GAME_OVER_RESULTS
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
        self._clear_movement()
        self._game.reset()
        self._mode = BreakoutSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._nickname = ""
        self._leaderboard = []
        self._status_message = None

    def _sync_paddle_direction(self) -> None:
        direction = 0
        if self._moving_left and not self._moving_right:
            direction = -1
        elif self._moving_right and not self._moving_left:
            direction = 1
        self._game.set_paddle_direction(direction)

    def _clear_movement(self) -> None:
        self._moving_left = False
        self._moving_right = False
        self._game.set_paddle_direction(0)

    def _is_allowed_nickname_character(self, character: str) -> bool:
        return character.isascii() and (
            character.isalnum() or character in ALLOWED_NICKNAME_CHARS
        )

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(self._elapsed * 1.6) + 1.0) / 2.0
        flare_x = int(APP_CONFIG.window_width * (0.18 + pulse * 0.06))
        flare_y = int(APP_CONFIG.window_height * (0.16 + pulse * 0.03))
        pygame.draw.circle(surface, (42, 56, 98), (flare_x, flare_y), int(98 + pulse * 18))
        pygame.draw.circle(
            surface,
            (31, 44, 81),
            (APP_CONFIG.window_width - 124, 104),
            112,
        )
        pygame.draw.rect(surface, (13, 20, 38), (0, 102, APP_CONFIG.window_width, 8))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(16, 16, APP_CONFIG.window_width - 32, 92)
        pygame.draw.rect(surface, HUD_PANEL, panel_rect, border_radius=24)
        pygame.draw.rect(surface, ACCENT, panel_rect, width=2, border_radius=24)

        title = self._title_font.render("Breakout", True, TEXT_MAIN)
        score = self._hud_font.render(f"Score {self._game.state.score:04d}", True, TEXT_MAIN)
        lives = self._hud_font.render(f"Lives {self._game.state.lives}", True, TEXT_STRONG)

        if self._game.state.phase is BreakoutPhase.WAITING:
            status_text = "Move with arrows / A D   •   Space or Enter to serve   •   Esc to menu"
        else:
            status_text = "Angle the paddle, clear every brick, and keep the ball alive"
        status_font = fit_font(
            status_text,
            max_width=panel_rect.width - 300,
            starting_size=26,
            min_size=18,
        )
        status = status_font.render(status_text, True, TEXT_MUTED)

        surface.blit(title, (34, 24))
        surface.blit(score, (34, 64))
        surface.blit(lives, (188, 64))
        surface.blit(status, (286, 42))

    def _draw_playfield(self, surface: pygame.Surface) -> None:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        width, height = APP_CONFIG.playfield_size
        playfield_rect = pygame.Rect(origin_x, origin_y, width, height)
        pygame.draw.rect(surface, PLAYFIELD, playfield_rect, border_radius=18)
        pygame.draw.rect(surface, ACCENT, playfield_rect, width=2, border_radius=18)

        self._draw_bricks(surface)
        self._draw_paddle(surface)
        self._draw_ball(surface)
        if self._game.state.phase is BreakoutPhase.WAITING:
            self._draw_serve_banner(surface, playfield_rect)

    def _draw_bricks(self, surface: pygame.Surface) -> None:
        for brick in self._game.state.bricks:
            brick_rect = self._screen_rect(brick.x, brick.y, brick.width, brick.height)
            base_color = BRICK_COLORS[brick.row % len(BRICK_COLORS)]
            highlight = tuple(min(component + 24, 255) for component in base_color)
            shadow = tuple(max(component - 38, 0) for component in base_color)
            pygame.draw.rect(surface, shadow, brick_rect, border_radius=8)
            inset = brick_rect.inflate(-4, -4)
            pygame.draw.rect(surface, base_color, inset, border_radius=7)
            shimmer = pygame.Rect(inset.x + 6, inset.y + 5, max(12, inset.width - 12), 5)
            pygame.draw.rect(surface, highlight, shimmer, border_radius=4)

    def _draw_paddle(self, surface: pygame.Surface) -> None:
        paddle_rect = self._screen_rect(
            self._game.state.paddle_center_x - PADDLE_WIDTH / 2.0,
            APP_CONFIG.playfield_size[1] - 22.0 - PADDLE_HEIGHT,
            PADDLE_WIDTH,
            PADDLE_HEIGHT,
        )
        pygame.draw.rect(surface, (57, 120, 152), paddle_rect, border_radius=10)
        inset = paddle_rect.inflate(-6, -4)
        pygame.draw.rect(surface, PADDLE, inset, border_radius=9)

    def _draw_ball(self, surface: pygame.Surface) -> None:
        center_x, center_y = self._screen_point(self._game.state.ball_position)
        pygame.draw.circle(surface, BALL, (center_x, center_y), int(BALL_RADIUS))
        pygame.draw.circle(surface, (255, 255, 255), (center_x - 2, center_y - 2), 3)

    def _draw_serve_banner(self, surface: pygame.Surface, playfield_rect: pygame.Rect) -> None:
        banner_rect = pygame.Rect(playfield_rect.x + 130, playfield_rect.y + 238, 444, 56)
        pygame.draw.rect(surface, (17, 31, 58), banner_rect, border_radius=18)
        pygame.draw.rect(surface, ACCENT_SOFT, banner_rect, width=2, border_radius=18)
        banner = self._banner_font.render("Press Space or Enter to launch the ball", True, TEXT_STRONG)
        surface.blit(banner, banner.get_rect(center=banner_rect.center))

    def _draw_outcome_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(APP_CONFIG.window_size, pygame.SRCALPHA)
        overlay.fill((*OVERLAY, 188))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(88, 120, 576, 448)
        pygame.draw.rect(surface, CARD_BACKGROUND, card_rect, border_radius=28)
        pygame.draw.rect(surface, ACCENT_SOFT, card_rect, width=2, border_radius=28)

        title = self._overlay_title_font.render(self._overlay_title(), True, TEXT_MAIN)
        score = self._overlay_font.render(
            f"Final score: {self._game.state.score}",
            True,
            TEXT_MAIN,
        )
        surface.blit(title, title.get_rect(center=(card_rect.centerx, card_rect.y + 52)))
        surface.blit(score, score.get_rect(center=(card_rect.centerx, card_rect.y + 104)))

        if self._mode is BreakoutSceneMode.ENTERING_NAME:
            self._draw_name_entry(surface, card_rect)
        else:
            self._draw_results(surface, card_rect)

    def _overlay_title(self) -> str:
        if self._game.state.phase is BreakoutPhase.WON:
            return "Wall Cleared"
        return "Game Over"

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
            return BRICK_COLORS[0]
        return BRICK_COLORS[3]

    def _screen_point(self, point: Vector) -> tuple[int, int]:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        return (round(origin_x + point.x), round(origin_y + point.y))

    def _screen_rect(self, x: float, y: float, width: float, height: float) -> pygame.Rect:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        return pygame.Rect(round(origin_x + x), round(origin_y + y), round(width), round(height))


def create_breakout_scene(score_store: LeaderboardStore) -> BreakoutScene:
    return BreakoutScene(score_store)
