from __future__ import annotations

from dataclasses import dataclass, field

import pygame
import pytest

from minigame_collection.games.blockfall import (
    BOARD_ROWS,
    BlockfallScene,
    BlockfallSceneMode,
    BlockfallState,
    FallingPiece,
    GridPoint,
    empty_board,
)
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
            ScoreEntry(player_name=player_name, score=score, created_at="2026-04-13T00:00:00+00:00"),
        )
        return True


def make_state(
    *,
    active_piece: FallingPiece | None,
    next_kind: str = "I",
    score: int = 0,
    lines_cleared: int = 0,
    level: int = 0,
    alive: bool = True,
) -> BlockfallState:
    return BlockfallState(
        board=empty_board(),
        active_piece=active_piece,
        next_kind=next_kind,
        score=score,
        lines_cleared=lines_cleared,
        level=level,
        alive=alive,
    )


def key_event(key: int, unicode: str = "") -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode)


def keyup_event(key: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYUP, key=key)


@pytest.fixture(autouse=True)
def init_pygame_font() -> None:
    pygame.font.init()
    yield
    pygame.font.quit()


def test_qualifying_score_enters_name_mode() -> None:
    scene = BlockfallScene(FakeScoreStore(qualifying_scores={4}))
    scene._game.state = make_state(active_piece=None, score=4, alive=False)

    scene.update(0.0)

    assert scene.mode is BlockfallSceneMode.ENTERING_NAME


def test_entering_valid_nickname_saves_score_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={5})
    scene = BlockfallScene(store)
    scene._game.state = make_state(active_piece=None, score=5, alive=False)
    scene.update(0.0)

    scene.handle_event(key_event(pygame.K_a, "A"))
    scene.handle_event(key_event(pygame.K_b, "b"))
    scene.handle_event(key_event(pygame.K_RETURN, "\r"))

    assert store.saved_scores == [("blockfall", "Ab", 5)]
    assert scene.mode is BlockfallSceneMode.GAME_OVER_RESULTS
    assert scene.leaderboard[0].player_name == "Ab"


def test_enter_from_results_restarts_fresh_run() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=None, score=9, lines_cleared=4, alive=False)
    scene.update(0.0)

    scene.handle_event(key_event(pygame.K_RETURN, "\r"))

    assert scene.mode is BlockfallSceneMode.PLAYING
    assert scene._game.state.alive is True
    assert scene._game.state.score == 0
    assert scene._game.state.active_piece is not None


def test_escape_from_active_play_returns_to_menu() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(
        active_piece=FallingPiece("T", 0, GridPoint(3, 0)),
        score=2,
        alive=True,
    )

    command = scene.handle_event(key_event(pygame.K_ESCAPE))

    assert isinstance(command, ShowMenu)


def test_horizontal_press_moves_immediately() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))

    scene.handle_event(key_event(pygame.K_LEFT))

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(2, 0))


def test_holding_horizontal_direction_repeats_after_delay_then_interval() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))

    scene.handle_event(key_event(pygame.K_LEFT))
    scene.update(0.15)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(2, 0))

    scene.update(0.01)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(1, 0))

    scene.update(0.06)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(0, 0))


def test_keyup_stops_horizontal_repeat() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))

    scene.handle_event(key_event(pygame.K_RIGHT))
    scene.update(0.16)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(5, 0))

    scene.handle_event(keyup_event(pygame.K_RIGHT))
    scene.update(0.20)

    assert scene._game.state.active_piece is not None
    assert scene._game.state.active_piece.position.x == 5


def test_latest_held_horizontal_direction_wins_and_release_falls_back() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(4, 0)))

    scene.handle_event(key_event(pygame.K_LEFT))
    scene.handle_event(key_event(pygame.K_RIGHT))
    scene.update(0.15)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(4, 0))

    scene.handle_event(keyup_event(pygame.K_RIGHT))

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))

    scene.update(0.15)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))

    scene.update(0.01)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(2, 0))


def test_holding_down_uses_faster_drop_than_normal_gravity() -> None:
    slow_scene = BlockfallScene(FakeScoreStore())
    slow_scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))

    fast_scene = BlockfallScene(FakeScoreStore())
    fast_scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))
    fast_scene.handle_event(key_event(pygame.K_DOWN))

    slow_scene.update(0.12)
    fast_scene.update(0.12)

    assert slow_scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))
    assert fast_scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 3))


def test_holding_down_starts_a_fresh_soft_drop_timer() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))

    scene.update(0.30)
    scene.handle_event(key_event(pygame.K_DOWN))
    scene.update(0.03)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))

    scene.update(0.01)

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 1))


def test_holding_down_does_not_pull_new_piece_past_spawn_position() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(
        active_piece=FallingPiece("O", 0, GridPoint(3, BOARD_ROWS - 3)),
        next_kind="I",
    )
    scene.handle_event(key_event(pygame.K_DOWN))

    scene.update(0.12)

    assert scene._game.state.active_piece == FallingPiece("I", 0, GridPoint(3, 0))


def test_held_input_is_ignored_outside_play_and_restart_clears_it() -> None:
    scene = BlockfallScene(FakeScoreStore())
    scene._game.state = make_state(active_piece=FallingPiece("O", 0, GridPoint(3, 0)))
    scene._held_left = True
    scene._held_down = True
    scene._horizontal_repeat_timers[-1] = 0.02
    scene._horizontal_priority = [-1]
    scene._mode = BlockfallSceneMode.GAME_OVER_RESULTS

    scene.handle_event(key_event(pygame.K_LEFT))
    scene.handle_event(keyup_event(pygame.K_LEFT))

    assert scene._game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))
    assert scene._held_left is True
    assert scene._held_down is True

    scene.handle_event(key_event(pygame.K_RETURN, "\r"))

    assert scene.mode is BlockfallSceneMode.PLAYING
    assert scene._held_left is False
    assert scene._held_right is False
    assert scene._held_down is False
    assert scene._horizontal_repeat_timers == {-1: 0.0, 1: 0.0}
    assert scene._horizontal_priority == []
