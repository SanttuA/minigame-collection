from __future__ import annotations

from ..registry import GameDefinition, GameRegistry
from ..scores import LeaderboardStore
from .breakout.scene import create_breakout_scene
from .blockfall.scene import create_blockfall_scene
from .snake.scene import create_snake_scene
from .starfighter.scene import create_starfighter_scene


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
            GameDefinition(
                id="breakout",
                title="Breakout",
                description="Angle the paddle, shatter the brick wall, and chase a high score.",
                create_scene=lambda: create_breakout_scene(score_store),
            ),
            GameDefinition(
                id="starfighter",
                title="Starfighter",
                description="Fly the lane, shred incoming waves, and survive the rising pressure.",
                create_scene=lambda: create_starfighter_scene(score_store),
            ),
        )
    )
