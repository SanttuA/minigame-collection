from pathlib import Path

from minigame_collection.games import build_game_registry
from minigame_collection.scores import SQLiteScoreStore


def test_registry_exposes_snake(tmp_path: Path) -> None:
    registry = build_game_registry(SQLiteScoreStore(tmp_path / "scores.db"))

    games = registry.list_games()

    assert len(games) == 2
    assert games[0].id == "snake"
    assert games[0].title == "Snake"
    assert callable(games[0].create_scene)
    assert games[1].id == "blockfall"
    assert games[1].title == "Blockfall"
    assert callable(games[1].create_scene)
