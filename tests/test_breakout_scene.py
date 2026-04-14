from __future__ import annotations

from dataclasses import dataclass, field, replace

import pygame
import pytest

from minigame_collection.games.breakout import BreakoutPhase, BreakoutScene, BreakoutSceneMode
from minigame_collection.scene import ShowMenu
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
            ScoreEntry(
                player_name=player_name,
                score=score,
                created_at="2026-04-14T00:00:00+00:00",
            ),
        )
        return True


def key_event(event_type: int, key: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(event_type, key=key, unicode=unicode)


@pytest.fixture(autouse=True)
def init_pygame_font() -> None:
    pygame.font.init()
    yield
    pygame.font.quit()


def test_space_launches_the_waiting_ball() -> None:
    scene = BreakoutScene(FakeScoreStore())

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_SPACE, " "))

    assert scene._game.state.phase is BreakoutPhase.PLAYING


def test_qualifying_score_enters_name_mode() -> None:
    scene = BreakoutScene(FakeScoreStore(qualifying_scores={400}))
    scene._game.state = replace(
        scene._game.state,
        phase=BreakoutPhase.LOST,
        score=400,
        lives=0,
    )

    scene.update(0.0)

    assert scene.mode is BreakoutSceneMode.ENTERING_NAME


def test_entering_valid_nickname_saves_breakout_score_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={500})
    scene = BreakoutScene(store)
    scene._game.state = replace(
        scene._game.state,
        phase=BreakoutPhase.WON,
        score=500,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_a, "A"))
    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_b, "b"))
    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RETURN, "\r"))

    assert store.saved_scores == [("breakout", "Ab", 500)]
    assert scene.mode is BreakoutSceneMode.GAME_OVER_RESULTS
    assert scene.leaderboard[0].player_name == "Ab"


def test_escape_skips_saving_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={350})
    scene = BreakoutScene(store)
    scene._game.state = replace(
        scene._game.state,
        phase=BreakoutPhase.LOST,
        score=350,
        lives=0,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert store.saved_scores == []
    assert scene.mode is BreakoutSceneMode.GAME_OVER_RESULTS


def test_enter_from_results_restarts_fresh_round() -> None:
    scene = BreakoutScene(FakeScoreStore())
    scene._game.state = replace(
        scene._game.state,
        phase=BreakoutPhase.LOST,
        score=120,
        lives=0,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RETURN, "\r"))

    assert scene.mode is BreakoutSceneMode.PLAYING
    assert scene._game.state.phase is BreakoutPhase.WAITING
    assert scene._game.state.score == 0
    assert scene._game.state.lives == 3
    assert len(scene._game.state.bricks) == 50


def test_escape_from_results_returns_to_menu() -> None:
    scene = BreakoutScene(FakeScoreStore())
    scene._game.state = replace(
        scene._game.state,
        phase=BreakoutPhase.LOST,
        lives=0,
    )
    scene.update(0.0)

    command = scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert isinstance(command, ShowMenu)
