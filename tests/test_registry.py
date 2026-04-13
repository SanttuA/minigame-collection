from minigame_collection.games import build_game_registry


def test_registry_exposes_snake() -> None:
    registry = build_game_registry()

    games = registry.list_games()

    assert len(games) == 1
    assert games[0].id == "snake"
    assert games[0].title == "Snake"
    assert callable(games[0].create_scene)
