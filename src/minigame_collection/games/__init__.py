from __future__ import annotations

from ..registry import GameDefinition, GameRegistry
from ..scores import LeaderboardStore
from .breakout.scene import create_breakout_scene
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
                id="breakout",
                title="Breakout",
                description="Angle the paddle, shatter the brick wall, and chase a high score.",
                create_scene=lambda: create_breakout_scene(score_store),
            ),
        )
    )
