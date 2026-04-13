from __future__ import annotations

from ..registry import GameDefinition, GameRegistry
from ..scores import LeaderboardStore
from .blockfall.scene import create_blockfall_scene
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
            GameDefinition(
                id="blockfall",
                title="Blockfall",
                description="Drop clean lines, survive the climb, and keep the stack under control.",
                create_scene=lambda: create_blockfall_scene(score_store),
            ),
        )
    )
