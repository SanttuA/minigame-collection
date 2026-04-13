from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from .scene import Scene


@dataclass(frozen=True, slots=True)
class GameDefinition:
    id: str
    title: str
    description: str
    create_scene: Callable[[], Scene]


class GameRegistry:
    def __init__(self, games: Sequence[GameDefinition]) -> None:
        self._games = tuple(games)
        game_ids = [game.id for game in self._games]
        if len(game_ids) != len(set(game_ids)):
            raise ValueError("Game ids must be unique.")
        self._by_id = {game.id: game for game in self._games}

    def list_games(self) -> tuple[GameDefinition, ...]:
        return self._games

    def get(self, game_id: str) -> GameDefinition:
        try:
            return self._by_id[game_id]
        except KeyError as exc:
            raise KeyError(f"Unknown game id: {game_id}") from exc
