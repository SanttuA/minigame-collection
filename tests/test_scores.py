from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from minigame_collection.metadata import APP_NAME
from minigame_collection.scores import LEADERBOARD_LIMIT, SQLiteScoreStore
from minigame_collection.scores import resolve_scores_database_path


def test_schema_is_initialized_for_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "scores.db"

    store = SQLiteScoreStore(database_path)

    assert store.available is True
    assert database_path.exists()

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'scores'"
        ).fetchone()

    assert row is not None


def test_saved_scores_are_ordered_by_score_then_oldest_first(tmp_path: Path) -> None:
    store = SQLiteScoreStore(tmp_path / "scores.db")

    assert store.save_score("snake", "alpha", 8) is True
    assert store.save_score("snake", "beta", 10) is True
    assert store.save_score("snake", "gamma", 10) is True

    leaderboard = store.top_scores("snake")

    assert [entry.player_name for entry in leaderboard] == ["beta", "gamma", "alpha"]
    assert [entry.score for entry in leaderboard] == [10, 10, 8]


def test_qualifies_matches_empty_partial_full_and_rejected_cases(tmp_path: Path) -> None:
    store = SQLiteScoreStore(tmp_path / "scores.db")

    assert store.qualifies("snake", 1) is True

    assert store.save_score("snake", "one", 10) is True
    assert store.save_score("snake", "two", 9) is True
    assert store.save_score("snake", "three", 8) is True

    assert store.qualifies("snake", 7) is True

    assert store.save_score("snake", "four", 7) is True
    assert store.save_score("snake", "five", 6) is True

    assert len(store.top_scores("snake", limit=LEADERBOARD_LIMIT)) == LEADERBOARD_LIMIT
    assert store.qualifies("snake", 7) is True
    assert store.qualifies("snake", 6) is False
    assert store.qualifies("snake", 0) is False


def test_top_scores_are_filtered_by_game_id(tmp_path: Path) -> None:
    store = SQLiteScoreStore(tmp_path / "scores.db")

    assert store.save_score("snake", "cobra", 12) is True
    assert store.save_score("blockfall", "block", 99) is True

    snake_scores = store.top_scores("snake")

    assert len(snake_scores) == 1
    assert snake_scores[0].player_name == "cobra"
    assert snake_scores[0].score == 12


def test_resolve_scores_database_path_uses_repo_root_for_source_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)

    expected = Path(__file__).resolve().parents[1] / "scores.db"

    assert resolve_scores_database_path() == expected


def test_resolve_scores_database_path_uses_localappdata_for_frozen_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Minigame Collection.exe"), raising=False)

    assert resolve_scores_database_path() == tmp_path / APP_NAME / "scores.db"
