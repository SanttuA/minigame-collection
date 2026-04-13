from __future__ import annotations

import math

import pygame

from ..config import APP_CONFIG
from ..registry import GameDefinition
from ..scene import LaunchGame, QuitApp, SceneCommand

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

        title = self._title_font.render("Minigame Collection", True, TEXT_MAIN)
        subtitle = self._subtitle_font.render(
            "Arcade-sized projects, one launcher. Start with Snake.",
            True,
            TEXT_MUTED,
        )
        surface.blit(title, (44, 40))
        surface.blit(subtitle, (46, 108))

        list_top = 188
        card_height = 128
        gap = 20

        for index, game in enumerate(self._games):
            y = list_top + index * (card_height + gap)
            selected = index == self._selected_index
            self._draw_game_card(surface, game, y, selected)

        hint = self._hint_font.render(
            "Use arrows or W/S to choose, Enter to play, Esc to quit",
            True,
            ACCENT_SOFT,
        )
        surface.blit(hint, (46, APP_CONFIG.window_height - 58))

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

        title = self._item_title_font.render(game.title, True, TEXT_MAIN)
        description = self._item_body_font.render(game.description, True, TEXT_MUTED)
        action = self._item_body_font.render(
            "Ready to launch" if selected else "Available in collection",
            True,
            ACCENT_SOFT if selected else TEXT_MUTED,
        )

        surface.blit(title, (card_rect.x + 98, card_rect.y + 22))
        surface.blit(description, (card_rect.x + 98, card_rect.y + 62))
        surface.blit(action, (card_rect.x + 98, card_rect.y + 90))
