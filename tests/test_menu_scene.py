from __future__ import annotations

import pygame
import pytest

from minigame_collection.config import APP_CONFIG
from minigame_collection.registry import GameDefinition
from minigame_collection.scenes.menu import MainMenuScene


def key_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key)


def make_games(count: int = 4) -> tuple[GameDefinition, ...]:
    return tuple(
        GameDefinition(
            id=f"game-{index}",
            title=f"Game {index + 1}",
            description=f"Description for game {index + 1}.",
            create_scene=lambda: None,
        )
        for index in range(count)
    )


@pytest.fixture(autouse=True)
def init_pygame_font() -> None:
    pygame.font.init()
    yield
    pygame.font.quit()


def test_selection_scrolls_to_keep_last_card_visible() -> None:
    scene = MainMenuScene(make_games())

    scene.handle_event(key_event(pygame.K_DOWN))
    scene.handle_event(key_event(pygame.K_DOWN))
    scene.handle_event(key_event(pygame.K_DOWN))

    assert scene._selected_index == 3
    assert scene._scroll_offset > 0.0


def test_wrapping_back_to_top_resets_scroll_offset() -> None:
    scene = MainMenuScene(make_games())

    for _ in range(3):
        scene.handle_event(key_event(pygame.K_DOWN))

    scene.handle_event(key_event(pygame.K_DOWN))

    assert scene._selected_index == 0
    assert scene._scroll_offset == 0.0


def test_menu_render_smoke_with_scrollable_list() -> None:
    scene = MainMenuScene(make_games())
    surface = pygame.Surface(APP_CONFIG.window_size)

    for _ in range(3):
        scene.handle_event(key_event(pygame.K_DOWN))

    scene.render(surface)
