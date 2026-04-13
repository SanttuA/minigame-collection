from __future__ import annotations

import math

import pygame

from ..config import APP_CONFIG
from ..registry import GameDefinition
from ..scene import LaunchGame, QuitApp, SceneCommand
from ..ui import fit_font

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
            return None
        if event.key in (pygame.K_DOWN, pygame.K_s):
            self._selected_index = (self._selected_index + 1) % len(self._games)
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
        subtitle_text = "Arcade-sized projects, one launcher. Start with Snake."
        subtitle_font = fit_font(
            subtitle_text,
            max_width=APP_CONFIG.window_width - 92,
            starting_size=34,
            min_size=26,
        )
        subtitle = subtitle_font.render(subtitle_text, True, TEXT_MUTED)
        surface.blit(title, (44, 38))
        surface.blit(subtitle, (46, 112))

        list_top = 188
        card_height = 128
        gap = 20

        for index, game in enumerate(self._games):
            y = list_top + index * (card_height + gap)
            selected = index == self._selected_index
            self._draw_game_card(surface, game, y, selected)

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

    def _draw_game_card(
        self,
        surface: pygame.Surface,
        game: GameDefinition,
        top: int,
        selected: bool,
    ) -> None:
        card_rect = pygame.Rect(40, top, APP_CONFIG.window_width - 80, 128)
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
