from __future__ import annotations

import math
from enum import Enum

import pygame

from ...config import APP_CONFIG
from ...scene import SceneCommand, ShowMenu
from ...scores import LEADERBOARD_LIMIT, LeaderboardStore, ScoreEntry
from ...ui import fit_font, wrap_text
from .logic import BOARD_COLUMNS, BOARD_ROWS, BlockfallGame, FallingPiece, GridPoint, piece_cells

BACKGROUND = (16, 10, 26)
BACKGROUND_GLOW = (66, 34, 92)
BOARD_BACKGROUND = (24, 18, 40)
BOARD_GRID = (59, 44, 86)
PANEL_BACKGROUND = (29, 21, 48)
PANEL_BORDER = (255, 190, 92)
TEXT_MAIN = (248, 242, 255)
TEXT_MUTED = (188, 175, 210)
TEXT_SOFT = (220, 203, 255)
OVERLAY = (8, 6, 16)
INPUT_BACKGROUND = (19, 14, 31)
SUCCESS = (118, 227, 163)
ERROR = (255, 117, 117)

BLOCKFALL_GAME_ID = "blockfall"
BOARD_CELL_SIZE = 24
BOARD_ORIGIN = (52, 132)
SIDE_PANEL = pygame.Rect(332, 132, 360, 480)
PREVIEW_BOX = pygame.Rect(350, 302, 146, 124)
NICKNAME_MAX_LENGTH = 8
ALLOWED_NICKNAME_CHARS = {" ", "-", "_"}
PIECE_COLORS = {
    "I": (104, 226, 255),
    "J": (96, 125, 255),
    "L": (255, 166, 77),
    "O": (255, 215, 78),
    "S": (101, 225, 133),
    "T": (191, 119, 255),
    "Z": (255, 103, 111),
}


def gravity_interval_for_level(level: int) -> float:
    return max(0.10, 0.55 - level * 0.04)


class BlockfallSceneMode(Enum):
    PLAYING = "playing"
    ENTERING_NAME = "entering_name"
    GAME_OVER_RESULTS = "game_over_results"


class BlockfallScene:
    def __init__(
        self,
        score_store: LeaderboardStore,
        *,
        game_id: str = BLOCKFALL_GAME_ID,
    ) -> None:
        self._score_store = score_store
        self._game_id = game_id
        self._game = BlockfallGame()
        self._mode = BlockfallSceneMode.PLAYING
        self._gravity_accumulator = 0.0
        self._elapsed = 0.0
        self._nickname = ""
        self._leaderboard: list[ScoreEntry] = []
        self._status_message: str | None = None
        self._title_font = pygame.font.Font(None, 60)
        self._stat_label_font = pygame.font.Font(None, 26)
        self._stat_value_font = pygame.font.Font(None, 44)
        self._panel_title_font = pygame.font.Font(None, 34)
        self._panel_font = pygame.font.Font(None, 28)
        self._overlay_title_font = pygame.font.Font(None, 68)
        self._overlay_font = pygame.font.Font(None, 32)
        self._leaderboard_title_font = pygame.font.Font(None, 34)
        self._leaderboard_font = pygame.font.Font(None, 30)
        self._input_font = pygame.font.Font(None, 38)
        self._status_font = pygame.font.Font(None, 28)

    @property
    def mode(self) -> BlockfallSceneMode:
        return self._mode

    @property
    def leaderboard(self) -> tuple[ScoreEntry, ...]:
        return tuple(self._leaderboard)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type != pygame.KEYDOWN:
            return None

        if self._mode is BlockfallSceneMode.PLAYING:
            return self._handle_playing_event(event)
        if self._mode is BlockfallSceneMode.ENTERING_NAME:
            return self._handle_name_entry_event(event)
        return self._handle_results_event(event)

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        if self._mode is not BlockfallSceneMode.PLAYING:
            return None
        if not self._game.state.alive:
            self._begin_post_game_flow()
            return None

        self._gravity_accumulator += delta_seconds
        interval = gravity_interval_for_level(self._game.state.level)
        while self._gravity_accumulator >= interval and self._game.state.alive:
            self._gravity_accumulator -= interval
            self._game.step()
            interval = gravity_interval_for_level(self._game.state.level)

        if not self._game.state.alive:
            self._begin_post_game_flow()
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_background(surface)
        self._draw_header(surface)
        self._draw_board(surface)
        self._draw_side_panel(surface)
        if self._mode is not BlockfallSceneMode.PLAYING:
            self._draw_game_over_overlay(surface)

    def _handle_playing_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            return ShowMenu()
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._game.move_horizontal(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._game.move_horizontal(1)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._game.soft_drop()
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._game.rotate_clockwise()

        if not self._game.state.alive:
            self._begin_post_game_flow()
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
            self._mode = BlockfallSceneMode.ENTERING_NAME
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
        self._mode = BlockfallSceneMode.GAME_OVER_RESULTS
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
        self._mode = BlockfallSceneMode.PLAYING
        self._gravity_accumulator = 0.0
        self._nickname = ""
        self._leaderboard = []
        self._status_message = None

    def _is_allowed_nickname_character(self, character: str) -> bool:
        return character.isascii() and (
            character.isalnum() or character in ALLOWED_NICKNAME_CHARS
        )

    def _draw_background(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(self._elapsed * 1.6) + 1.0) / 2.0
        pygame.draw.circle(
            surface,
            BACKGROUND_GLOW,
            (APP_CONFIG.window_width - 90, 92),
            int(98 + pulse * 18),
        )
        pygame.draw.circle(surface, (44, 21, 60), (110, 590), 114)
        pygame.draw.rect(surface, (21, 14, 34), (0, 112, APP_CONFIG.window_width, 8))

    def _draw_header(self, surface: pygame.Surface) -> None:
        title = self._title_font.render("Blockfall", True, TEXT_MAIN)
        subtitle_text = "Stack clean lines before the well runs out of room."
        subtitle_font = fit_font(
            subtitle_text,
            max_width=APP_CONFIG.window_width - 108,
            starting_size=28,
            min_size=22,
        )
        subtitle = subtitle_font.render(subtitle_text, True, TEXT_MUTED)
        surface.blit(title, (48, 34))
        surface.blit(subtitle, (50, 84))

    def _draw_board(self, surface: pygame.Surface) -> None:
        board_rect = pygame.Rect(
            BOARD_ORIGIN[0],
            BOARD_ORIGIN[1],
            BOARD_COLUMNS * BOARD_CELL_SIZE,
            BOARD_ROWS * BOARD_CELL_SIZE,
        )
        pygame.draw.rect(surface, BOARD_BACKGROUND, board_rect, border_radius=20)
        pygame.draw.rect(surface, PANEL_BORDER, board_rect, width=2, border_radius=20)

        for column in range(1, BOARD_COLUMNS):
            x = board_rect.x + column * BOARD_CELL_SIZE
            pygame.draw.line(surface, BOARD_GRID, (x, board_rect.y), (x, board_rect.bottom), 1)
        for row in range(1, BOARD_ROWS):
            y = board_rect.y + row * BOARD_CELL_SIZE
            pygame.draw.line(surface, BOARD_GRID, (board_rect.x, y), (board_rect.right, y), 1)

        for row_index, row in enumerate(self._game.state.board):
            for column_index, kind in enumerate(row):
                if kind is None:
                    continue
                self._draw_block(surface, GridPoint(column_index, row_index), PIECE_COLORS[kind])

        active_piece = self._game.state.active_piece
        if active_piece is not None:
            for cell in piece_cells(active_piece):
                self._draw_block(surface, cell, PIECE_COLORS[active_piece.kind])

    def _draw_side_panel(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, PANEL_BACKGROUND, SIDE_PANEL, border_radius=24)
        pygame.draw.rect(surface, PANEL_BORDER, SIDE_PANEL, width=2, border_radius=24)

        self._draw_stat(
            surface,
            label="Score",
            value=str(self._game.state.score),
            top=SIDE_PANEL.y + 24,
        )
        self._draw_stat(
            surface,
            label="Lines",
            value=str(self._game.state.lines_cleared),
            top=SIDE_PANEL.y + 104,
        )
        self._draw_stat(
            surface,
            label="Level",
            value=str(self._game.state.level),
            top=SIDE_PANEL.y + 184,
        )

        preview_title = self._panel_title_font.render("Next Piece", True, TEXT_MAIN)
        surface.blit(preview_title, (PREVIEW_BOX.x, PREVIEW_BOX.y - 32))
        pygame.draw.rect(surface, INPUT_BACKGROUND, PREVIEW_BOX, border_radius=18)
        pygame.draw.rect(surface, PANEL_BORDER, PREVIEW_BOX, width=2, border_radius=18)
        self._draw_preview_piece(surface, self._game.state.next_kind)

        controls_title = self._panel_title_font.render("Controls", True, TEXT_MAIN)
        surface.blit(controls_title, (PREVIEW_BOX.x, PREVIEW_BOX.bottom + 22))

        controls = [
            "Left / A  Move left",
            "Right / D  Move right",
            "Down / S  Soft drop",
            "Up / W  Rotate",
            "Esc  Return to menu",
        ]
        top = PREVIEW_BOX.bottom + 58
        for index, line in enumerate(controls):
            label = self._panel_font.render(line, True, TEXT_SOFT)
            surface.blit(label, (PREVIEW_BOX.x, top + index * 30))

        speed_text = f"Gravity {gravity_interval_for_level(self._game.state.level):.2f}s"
        speed = self._panel_font.render(speed_text, True, TEXT_MUTED)
        surface.blit(speed, (PREVIEW_BOX.x, SIDE_PANEL.bottom - 42))

    def _draw_stat(self, surface: pygame.Surface, *, label: str, value: str, top: int) -> None:
        label_surface = self._stat_label_font.render(label.upper(), True, TEXT_MUTED)
        value_surface = self._stat_value_font.render(value, True, TEXT_MAIN)
        surface.blit(label_surface, (SIDE_PANEL.x + 18, top))
        surface.blit(value_surface, (SIDE_PANEL.x + 18, top + 22))

    def _draw_preview_piece(self, surface: pygame.Surface, kind: str) -> None:
        preview_piece = FallingPiece(kind=kind, rotation=0, position=GridPoint(0, 0))
        cells = piece_cells(preview_piece)
        min_x = min(cell.x for cell in cells)
        max_x = max(cell.x for cell in cells)
        min_y = min(cell.y for cell in cells)
        max_y = max(cell.y for cell in cells)
        width = (max_x - min_x + 1) * 18
        height = (max_y - min_y + 1) * 18
        origin_x = PREVIEW_BOX.centerx - width // 2
        origin_y = PREVIEW_BOX.centery - height // 2

        for cell in cells:
            rect = pygame.Rect(
                origin_x + (cell.x - min_x) * 18,
                origin_y + (cell.y - min_y) * 18,
                18,
                18,
            ).inflate(-2, -2)
            pygame.draw.rect(surface, PIECE_COLORS[kind], rect, border_radius=5)

    def _draw_block(self, surface: pygame.Surface, point: GridPoint, color: tuple[int, int, int]) -> None:
        rect = pygame.Rect(
            BOARD_ORIGIN[0] + point.x * BOARD_CELL_SIZE,
            BOARD_ORIGIN[1] + point.y * BOARD_CELL_SIZE,
            BOARD_CELL_SIZE,
            BOARD_CELL_SIZE,
        ).inflate(-4, -4)
        pygame.draw.rect(surface, color, rect, border_radius=7)

    def _draw_game_over_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(APP_CONFIG.window_size, pygame.SRCALPHA)
        overlay.fill((*OVERLAY, 190))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(88, 112, 576, 456)
        pygame.draw.rect(surface, PANEL_BACKGROUND, card_rect, border_radius=28)
        pygame.draw.rect(surface, PANEL_BORDER, card_rect, width=2, border_radius=28)

        title = self._overlay_title_font.render("Game Over", True, TEXT_MAIN)
        score = self._overlay_font.render(
            f"Final score: {self._game.state.score}",
            True,
            TEXT_MAIN,
        )
        surface.blit(title, title.get_rect(center=(card_rect.centerx, card_rect.y + 54)))
        surface.blit(score, score.get_rect(center=(card_rect.centerx, card_rect.y + 106)))

        if self._mode is BlockfallSceneMode.ENTERING_NAME:
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
        prompt = prompt_font.render(prompt_text, True, PANEL_BORDER)
        surface.blit(prompt, prompt.get_rect(center=(card_rect.centerx, card_rect.y + 170)))

        input_rect = pygame.Rect(card_rect.x + 96, card_rect.y + 214, card_rect.width - 192, 62)
        pygame.draw.rect(surface, INPUT_BACKGROUND, input_rect, border_radius=16)
        pygame.draw.rect(surface, PANEL_BORDER, input_rect, width=2, border_radius=16)

        nickname = self._nickname or "Type up to 8 chars"
        nickname_color = TEXT_MAIN if self._nickname else TEXT_MUTED
        nickname_surface = self._input_font.render(nickname, True, nickname_color)
        surface.blit(nickname_surface, (input_rect.x + 16, input_rect.y + 11))

        if self._nickname and int(self._elapsed * 2.4) % 2 == 0:
            cursor_x = input_rect.x + 18 + nickname_surface.get_width()
            pygame.draw.line(
                surface,
                TEXT_SOFT,
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
            rank = self._leaderboard_font.render(f"{index:02d}", True, PANEL_BORDER)
            name = self._leaderboard_font.render(entry.player_name, True, TEXT_MAIN)
            score = self._leaderboard_font.render(str(entry.score), True, TEXT_MAIN)
            surface.blit(rank, (rank_x, y))
            surface.blit(name, (name_x, y))
            surface.blit(score, score.get_rect(topright=(score_x, y)))

    def _status_color(self, message: str) -> tuple[int, int, int]:
        if "unavailable" in message.lower():
            return ERROR
        return SUCCESS


def create_blockfall_scene(score_store: LeaderboardStore) -> BlockfallScene:
    return BlockfallScene(score_store)
