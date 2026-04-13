from __future__ import annotations

from dataclasses import dataclass, field

import pygame
import pytest

from minigame_collection.games.snake import Direction, Point, SnakeScene, SnakeSceneMode, SnakeState
from minigame_collection.scores import ScoreEntry


@dataclass
class FakeScoreStore:
    available: bool = True
    qualifying_scores: set[int] = field(default_factory=set)
    leaderboard_entries: list[ScoreEntry] = field(default_factory=list)
    saved_scores: list[tuple[str, str, int]] = field(default_factory=list)

    def top_scores(self, game_id: str, limit: int = 5) -> list[ScoreEntry]:
        return self.leaderboard_entries[:limit]

    def qualifies(self, game_id: str, score: int, limit: int = 5) -> bool:
        return score in self.qualifying_scores

    def save_score(self, game_id: str, player_name: str, score: int) -> bool:
        self.saved_scores.append((game_id, player_name, score))
        self.leaderboard_entries.insert(
            0,
            ScoreEntry(player_name=player_name, score=score, created_at="2026-04-13T00:00:00+00:00"),
        )
        return True


def make_state(
    body: tuple[Point, ...],
    direction: Direction,
    food: Point | None,
    *,
    score: int = 0,
    alive: bool = True,
    pending_direction: Direction | None = None,
) -> SnakeState:
    return SnakeState(
        body=body,
        direction=direction,
        pending_direction=pending_direction or direction,
        food=food,
        score=score,
        alive=alive,
    )


def key_event(key: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


@pytest.fixture(autouse=True)
def init_pygame_font() -> None:
    pygame.font.init()
    yield
    pygame.font.quit()


def test_non_positive_score_goes_straight_to_results() -> None:
    scene = SnakeScene(FakeScoreStore(qualifying_scores={0}))
    scene._game.state = make_state(
        body=(Point(5, 5), Point(4, 5), Point(3, 5)),
        direction=Direction.RIGHT,
        food=Point(8, 8),
        score=0,
        alive=False,
    )

    scene.update(0.0)

    assert scene.mode is SnakeSceneMode.GAME_OVER_RESULTS


def test_qualifying_score_enters_name_mode() -> None:
    scene = SnakeScene(FakeScoreStore(qualifying_scores={4}))
    scene._game.state = make_state(
        body=(Point(5, 5), Point(4, 5), Point(3, 5)),
        direction=Direction.RIGHT,
        food=Point(8, 8),
        score=4,
        alive=False,
    )

    scene.update(0.0)

    assert scene.mode is SnakeSceneMode.ENTERING_NAME


def test_entering_valid_nickname_saves_score_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={5})
    scene = SnakeScene(store)
    scene._game.state = make_state(
        body=(Point(5, 5), Point(4, 5), Point(3, 5)),
        direction=Direction.RIGHT,
        food=Point(8, 8),
        score=5,
        alive=False,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.K_a, "A"))
    scene.handle_event(key_event(pygame.K_b, "b"))
    scene.handle_event(key_event(pygame.K_RETURN, "\r"))

    assert store.saved_scores == [("snake", "Ab", 5)]
    assert scene.mode is SnakeSceneMode.GAME_OVER_RESULTS
    assert scene.leaderboard[0].player_name == "Ab"


def test_escape_skips_saving_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={3})
    scene = SnakeScene(store)
    scene._game.state = make_state(
        body=(Point(5, 5), Point(4, 5), Point(3, 5)),
        direction=Direction.RIGHT,
        food=Point(8, 8),
        score=3,
        alive=False,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.K_ESCAPE))

    assert store.saved_scores == []
    assert scene.mode is SnakeSceneMode.GAME_OVER_RESULTS


def test_enter_from_results_restarts_fresh_run() -> None:
    scene = SnakeScene(FakeScoreStore())
    scene._game.state = make_state(
        body=(Point(8, 5), Point(7, 5), Point(6, 5), Point(5, 5)),
        direction=Direction.RIGHT,
        food=Point(9, 5),
        score=6,
        alive=False,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.K_RETURN, "\r"))

    assert scene.mode is SnakeSceneMode.PLAYING
    assert scene._game.state.alive is True
    assert scene._game.state.score == 0
    assert len(scene._game.state.body) == 3
