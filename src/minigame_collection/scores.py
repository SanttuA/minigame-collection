from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


LEADERBOARD_LIMIT = 5


@dataclass(frozen=True, slots=True)
class ScoreEntry:
    player_name: str
    score: int
    created_at: str


class LeaderboardStore(Protocol):
    @property
    def available(self) -> bool:
        ...

    def top_scores(self, game_id: str, limit: int = LEADERBOARD_LIMIT) -> list[ScoreEntry]:
        ...

    def qualifies(self, game_id: str, score: int, limit: int = LEADERBOARD_LIMIT) -> bool:
        ...

    def save_score(
        self,
        game_id: str,
        player_name: str,
        score: int,
    ) -> bool:
        ...


class SQLiteScoreStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._available = False
        self._initialize()

    @property
    def available(self) -> bool:
        return self._available

    def top_scores(self, game_id: str, limit: int = LEADERBOARD_LIMIT) -> list[ScoreEntry]:
        if not self._available:
            return []

        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT player_name, score, created_at
                    FROM scores
                    WHERE game_id = ?
                    ORDER BY score DESC, created_at ASC, id ASC
                    LIMIT ?
                    """,
                    (game_id, limit),
                ).fetchall()
        except (OSError, sqlite3.Error):
            self._available = False
            return []

        return [
            ScoreEntry(
                player_name=row["player_name"],
                score=row["score"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def qualifies(self, game_id: str, score: int, limit: int = LEADERBOARD_LIMIT) -> bool:
        if not self._available or score <= 0 or limit < 1:
            return False

        leaderboard = self.top_scores(game_id, limit=limit)
        if not self._available:
            return False
        if len(leaderboard) < limit:
            return True
        return score > leaderboard[-1].score

    def save_score(self, game_id: str, player_name: str, score: int) -> bool:
        if not self._available or score <= 0:
            return False

        trimmed_name = player_name.strip()
        if not trimmed_name:
            return False

        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO scores (game_id, player_name, score, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        game_id,
                        trimmed_name,
                        score,
                        datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    ),
                )
                connection.commit()
        except (OSError, sqlite3.Error):
            self._available = False
            return False

        return True

    def _initialize(self) -> None:
        try:
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scores (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_id TEXT NOT NULL,
                        player_name TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
        except (OSError, sqlite3.Error):
            self._available = False
            return

        self._available = True

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection


def resolve_scores_database_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "scores.db"
    return Path(__file__).resolve().parents[2] / "scores.db"
