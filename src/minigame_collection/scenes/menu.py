from __future__ import annotations

import math

import pygame

from ..config import APP_CONFIG
from ..registry import GameDefinition
from ..scene import LaunchGame, QuitApp, SceneCommand
from ..ui import fit_font

LIST_TOP = 188
LIST_BOTTOM_MARGIN = 92
CARD_HEIGHT = 128
CARD_GAP = 20
CARD_SIDE_MARGIN = 40
SCROLLBAR_WIDTH = 8

BACKGROUND = (7, 14, 26)
PANEL = (15, 28, 46)
PANEL_SELECTED = (29, 52, 84)
TEXT_MAIN = (244, 248, 255)
TEXT_MUTED = (157, 182, 211)
ACCENT = (243, 180, 60)
ACCENT_SOFT = (255, 217, 135)


class MainMenuScene:
    def __init__(self, games: tuple[GameDefinition, ...]) -> None:
        self._games = games
        self._selected_index = 0
        self._scroll_offset = 0.0
        self._elapsed = 0.0
        self._title_font = pygame.font.Font(None, 78)
        self._subtitle_font = pygame.font.Font(None, 34)
        self._item_title_font = pygame.font.Font(None, 42)
        self._item_body_font = pygame.font.Font(None, 28)
        self._hint_font = pygame.font.Font(None, 30)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type != pygame.KEYDOWN:
            return None

        if event.key in (pygame.K_UP, pygame.K_w):
            self._selected_index = (self._selected_index - 1) % len(self._games)
            self._ensure_selection_visible()
            return None
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected_index = (self._selected_index + 1) % len(self._games)
            self._ensure_selection_visible()
            return None
        if event.key == pygame.K_RETURN:
            return LaunchGame(self._games[self._selected_index].id)
        if event.key == pygame.K_ESCAPE:
            return QuitApp()
        return None

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_background(surface)

        title_text = "Minigame Collection"
        title_font = fit_font(
            title_text,
            max_width=APP_CONFIG.window_width - 88,
            starting_size=78,
            min_size=62,
        )
        title = title_font.render(title_text, True, TEXT_MAIN)
        subtitle_text = "Arcade-sized projects, one launcher. Pick a cabinet and jump in."
        subtitle_font = fit_font(
            subtitle_text,
            max_width=APP_CONFIG.window_width - 92,
            starting_size=34,
            min_size=26,
        )
        subtitle = subtitle_font.render(subtitle_text, True, TEXT_MUTED)
        surface.blit(title, (44, 38))
        surface.blit(subtitle, (46, 112))

        self._draw_game_list(surface)

        hint_text = "Use arrows or W/S to choose, Enter to play, Esc to quit"
        hint_font = fit_font(
            hint_text,
            max_width=APP_CONFIG.window_width - 92,
            starting_size=30,
            min_size=22,
        )
        hint = hint_font.render(hint_text, True, ACCENT_SOFT)
        surface.blit(
            hint,
            hint.get_rect(center=(APP_CONFIG.window_width // 2, APP_CONFIG.window_height - 48)),
        )

    def _draw_background(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(self._elapsed * 1.4) + 1.0) / 2.0
        pygame.draw.circle(
            surface,
            (18, 39, 68),
            (APP_CONFIG.window_width - 110, 90),
            int(110 + pulse * 14),
        )
        pygame.draw.circle(surface, (26, 62, 103), (118, 590), 96)
        pygame.draw.rect(surface, (12, 22, 38), (0, 148, APP_CONFIG.window_width, 10))

    def _draw_game_list(self, surface: pygame.Surface) -> None:
        viewport_rect = self._list_viewport_rect()
        previous_clip = surface.get_clip()
        surface.set_clip(viewport_rect)

        for index, game in enumerate(self._games):
            y = viewport_rect.y + index * (CARD_HEIGHT + CARD_GAP) - round(self._scroll_offset)
            selected = index == self._selected_index
            self._draw_game_card(surface, game, y, selected)

        surface.set_clip(previous_clip)
        self._draw_scrollbar(surface, viewport_rect)

    def _draw_scrollbar(self, surface: pygame.Surface, viewport_rect: pygame.Rect) -> None:
        max_scroll = self._max_scroll_offset()
        if max_scroll <= 0.0:
            return

        track_rect = pygame.Rect(
            APP_CONFIG.window_width - 24,
            viewport_rect.y,
            SCROLLBAR_WIDTH,
            viewport_rect.height,
        )
        handle_height = max(48, round(viewport_rect.height * (viewport_rect.height / self._content_height())))
        handle_travel = track_rect.height - handle_height
        progress = self._scroll_offset / max_scroll if max_scroll > 0.0 else 0.0
        handle_y = track_rect.y + round(handle_travel * progress)
        handle_rect = pygame.Rect(track_rect.x, handle_y, track_rect.width, handle_height)

        pygame.draw.rect(surface, (18, 31, 49), track_rect, border_radius=6)
        pygame.draw.rect(surface, (62, 98, 142), handle_rect, border_radius=6)

    def _list_viewport_rect(self) -> pygame.Rect:
        return pygame.Rect(
            CARD_SIDE_MARGIN,
            LIST_TOP,
            APP_CONFIG.window_width - CARD_SIDE_MARGIN * 2,
            APP_CONFIG.window_height - LIST_TOP - LIST_BOTTOM_MARGIN,
        )

    def _content_height(self) -> int:
        if not self._games:
            return 0
        return len(self._games) * CARD_HEIGHT + (len(self._games) - 1) * CARD_GAP

    def _max_scroll_offset(self) -> float:
        viewport_height = self._list_viewport_rect().height
        return float(max(0, self._content_height() - viewport_height))

    def _ensure_selection_visible(self) -> None:
        viewport_height = self._list_viewport_rect().height
        selected_top = self._selected_index * (CARD_HEIGHT + CARD_GAP)
        selected_bottom = selected_top + CARD_HEIGHT

        if selected_top < self._scroll_offset:
            self._scroll_offset = float(selected_top)
        elif selected_bottom > self._scroll_offset + viewport_height:
            self._scroll_offset = float(selected_bottom - viewport_height)

        self._scroll_offset = max(0.0, min(self._scroll_offset, self._max_scroll_offset()))

    def _draw_game_card(
        self,
        surface: pygame.Surface,
        game: GameDefinition,
        top: int,
        selected: bool,
    ) -> None:
        card_rect = pygame.Rect(CARD_SIDE_MARGIN, top, APP_CONFIG.window_width - 80, CARD_HEIGHT)
        fill = PANEL_SELECTED if selected else PANEL
        border = ACCENT if selected else (37, 68, 102)
        pygame.draw.rect(surface, fill, card_rect, border_radius=26)
        pygame.draw.rect(surface, border, card_rect, width=2, border_radius=26)

        badge_rect = pygame.Rect(card_rect.x + 18, card_rect.y + 18, 60, 92)
        pygame.draw.rect(surface, border, badge_rect, border_radius=18)
        badge_label = f"{self._games.index(game) + 1:02d}"
        number = self._item_title_font.render(badge_label, True, BACKGROUND)
        surface.blit(number, number.get_rect(center=badge_rect.center))

        content_left = card_rect.x + 98
        content_width = card_rect.right - 28 - content_left
        title = self._item_title_font.render(game.title, True, TEXT_MAIN)
        description_font = fit_font(
            game.description,
            max_width=content_width,
            starting_size=28,
            min_size=20,
        )
        description = description_font.render(game.description, True, TEXT_MUTED)
        action = self._item_body_font.render(
            "Ready to launch" if selected else "Available in collection",
            True,
            ACCENT_SOFT if selected else TEXT_MUTED,
        )

        title_y = card_rect.y + 20
        description_y = title_y + title.get_height() + 10
        action_y = description_y + description.get_height() + 10

        surface.blit(title, (content_left, title_y))
        surface.blit(description, (content_left, description_y))
        surface.blit(action, (content_left, action_y))
