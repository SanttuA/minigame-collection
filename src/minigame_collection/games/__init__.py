from __future__ import annotations

from ..registry import GameDefinition, GameRegistry
from ..scores import LeaderboardStore
from .snake.scene import create_snake_scene


def build_game_registry(score_store: LeaderboardStore) -> GameRegistry:
    return GameRegistry(
        (
            GameDefinition(
                id="snake",
                title="Snake",
                description="Grow longer, dodge the walls, and keep up as the pace climbs.",
                create_scene=lambda: create_snake_scene(score_store),
            ),
        )
    )
