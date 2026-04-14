from pathlib import Path

from minigame_collection.games import build_game_registry
from minigame_collection.scores import SQLiteScoreStore


def test_registry_exposes_snake(tmp_path: Path) -> None:
    registry = build_game_registry(SQLiteScoreStore(tmp_path / "scores.db"))

    games = registry.list_games()

    assert [game.id for game in games] == ["snake", "blockfall", "breakout", "starfighter"]
    assert [game.title for game in games] == ["Snake", "Blockfall", "Breakout", "Starfighter"]
    assert all(callable(game.create_scene) for game in games)
