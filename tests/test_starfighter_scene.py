from __future__ import annotations

from dataclasses import dataclass, field, replace

import pygame
import pytest

from minigame_collection.config import APP_CONFIG
from minigame_collection.games.starfighter.logic import Mine, Projectile, StarfighterPhase, Vector
from minigame_collection.games.starfighter.scene import StarfighterScene, StarfighterSceneMode
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


def test_escape_from_active_play_returns_to_menu() -> None:
    scene = StarfighterScene(FakeScoreStore())

    command = scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert isinstance(command, ShowMenu)


def test_held_direction_moves_ship_and_keyup_stops_motion() -> None:
    scene = StarfighterScene(FakeScoreStore())
    starting_x = scene._game.state.player_position.x

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RIGHT))
    scene.update(0.20)

    assert scene._game.state.player_position.x > starting_x

    scene.handle_event(key_event(pygame.KEYUP, pygame.K_RIGHT))
    stopped_x = scene._game.state.player_position.x
    scene.update(0.10)

    assert scene._game.state.player_position.x == pytest.approx(stopped_x)


def test_qualifying_score_enters_name_mode() -> None:
    scene = StarfighterScene(FakeScoreStore(qualifying_scores={480}))
    scene._game.state = replace(
        scene._game.state,
        phase=StarfighterPhase.LOST,
        score=480,
        shields=0,
    )

    scene.update(0.0)

    assert scene.mode is StarfighterSceneMode.ENTERING_NAME


def test_entering_valid_nickname_saves_score_and_shows_results() -> None:
    store = FakeScoreStore(qualifying_scores={650})
    scene = StarfighterScene(store)
    scene._game.state = replace(
        scene._game.state,
        phase=StarfighterPhase.LOST,
        score=650,
        shields=0,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_a, "A"))
    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_b, "b"))
    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RETURN, "\r"))

    assert store.saved_scores == [("starfighter", "Ab", 650)]
    assert scene.mode is StarfighterSceneMode.GAME_OVER_RESULTS
    assert scene.leaderboard[0].player_name == "Ab"


def test_enter_from_results_restarts_fresh_run() -> None:
    scene = StarfighterScene(FakeScoreStore())
    scene._game.state = replace(
        scene._game.state,
        phase=StarfighterPhase.LOST,
        score=350,
        shields=0,
    )
    scene.update(0.0)

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RETURN, "\r"))

    assert scene.mode is StarfighterSceneMode.PLAYING
    assert scene._game.state.phase is StarfighterPhase.PLAYING
    assert scene._game.state.score == 0
    assert scene._game.state.shields == 3
    assert scene._game.state.enemies == ()
    assert scene._game.state.mines == ()


def test_escape_from_results_returns_to_menu() -> None:
    scene = StarfighterScene(FakeScoreStore())
    scene._game.state = replace(
        scene._game.state,
        phase=StarfighterPhase.LOST,
        shields=0,
    )
    scene.update(0.0)

    command = scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_ESCAPE))

    assert isinstance(command, ShowMenu)


def test_held_input_is_ignored_outside_play_and_restart_clears_it() -> None:
    scene = StarfighterScene(FakeScoreStore())
    scene._held_left = True
    scene._held_up = True
    original_position = scene._game.state.player_position
    scene._mode = StarfighterSceneMode.GAME_OVER_RESULTS

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_LEFT))
    scene.handle_event(key_event(pygame.KEYUP, pygame.K_LEFT))

    assert scene._game.state.player_position == original_position
    assert scene._held_left is True
    assert scene._held_up is True

    scene.handle_event(key_event(pygame.KEYDOWN, pygame.K_RETURN, "\r"))

    assert scene.mode is StarfighterSceneMode.PLAYING
    assert scene._held_left is False
    assert scene._held_right is False
    assert scene._held_up is False
    assert scene._held_down is False


def test_render_smoke_for_play_and_results() -> None:
    scene = StarfighterScene(FakeScoreStore())
    surface = pygame.Surface(APP_CONFIG.window_size)
    scene._game.state = replace(
        scene._game.state,
        mines=(Mine(position=Vector(420.0, 220.0), ttl=3.0, pulse=0.0),),
        enemy_projectiles=(
            Projectile(position=Vector(360.0, 160.0), velocity=Vector(-240.0, 120.0), radius=6.0),
        ),
    )

    scene.render(surface)

    scene._game.state = replace(
        scene._game.state,
        phase=StarfighterPhase.LOST,
        score=240,
        shields=0,
    )
    scene.update(0.0)
    scene.render(surface)
