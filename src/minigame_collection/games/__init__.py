from __future__ import annotations

from ..registry import GameDefinition, GameRegistry
from .snake.scene import create_snake_scene


def build_game_registry() -> GameRegistry:
    return GameRegistry(
        (
            GameDefinition(
                id="snake",
                title="Snake",
                description="Grow longer, dodge the walls, and keep up as the pace climbs.",
                create_scene=create_snake_scene,
            ),
        )
    )
