from __future__ import annotations

import random
from dataclasses import replace

import pytest

from minigame_collection.games.starfighter.logic import (
    DRONE_SCORE,
    ENEMY_PROJECTILE_RADIUS,
    ENEMY_PROJECTILE_SPEED,
    FULL_SHIELD_SCORE_BONUS,
    GUNSHIP_SCORE,
    MAX_SHIELDS,
    MINE_RADIUS,
    PICKUP_SCORE_BONUS,
    PLAYER_RADIUS,
    Projectile,
    Pickup,
    PickupType,
    START_SCROLL_SPEED,
    START_SPAWN_INTERVAL,
    SWOOPER_SCORE,
    TARGETED_JITTER,
    Enemy,
    EnemyKind,
    Mine,
    StarfighterGame,
    StarfighterPhase,
    Vector,
    pickup_for_kill_count,
)

BOARD_WIDTH = 704
BOARD_HEIGHT = 512


def make_game(seed: int = 3) -> StarfighterGame:
    return StarfighterGame(BOARD_WIDTH, BOARD_HEIGHT, rng=random.Random(seed))


def test_initial_state_starts_in_playing_mode() -> None:
    game = make_game()

    assert game.state.phase is StarfighterPhase.PLAYING
    assert game.state.shields == MAX_SHIELDS
    assert game.state.weapon_level == 1
    assert game.state.score == 0
    assert game.state.distance == 0
    assert game.state.kills == 0
    assert game.state.enemies == ()
    assert game.state.pickups == ()
    assert game.state.mines == ()
    assert game.current_scroll_speed == START_SCROLL_SPEED
    assert game.current_spawn_interval == START_SPAWN_INTERVAL


def test_player_movement_clamps_to_playfield_edges() -> None:
    game = make_game()
    game._spawn_timer = 999.0

    game.set_movement(-1, -1)
    game.step(2.0)

    assert game.state.player_position == Vector(PLAYER_RADIUS, PLAYER_RADIUS)

    game.set_movement(1, 1)
    game.step(4.0)

    assert game.state.player_position == Vector(
        BOARD_WIDTH - PLAYER_RADIUS,
        BOARD_HEIGHT - PLAYER_RADIUS,
    )


def test_auto_fire_cadence_respects_weapon_levels() -> None:
    game = make_game()
    game._spawn_timer = 999.0

    game.step(0.01)
    assert len(game.state.player_projectiles) == 1

    game.step(0.16)
    assert len(game.state.player_projectiles) == 1

    game.step(0.02)
    assert len(game.state.player_projectiles) == 2

    game.reset()
    game._spawn_timer = 999.0
    game.state = replace(game.state, weapon_level=3)

    game.step(0.01)
    assert len(game.state.player_projectiles) == 2

    game.step(0.11)
    assert len(game.state.player_projectiles) == 4


def test_targeted_wave_spawns_near_player_lane_after_six_seconds() -> None:
    game = make_game()
    player = Vector(140.0, 230.0)
    game._wave_count = 5

    enemies, mines = game._spawn_wave(6.1, player)

    assert mines == []
    assert enemies
    assert any(abs(enemy.base_y - player.y) <= TARGETED_JITTER + 1.0 for enemy in enemies)


def test_minefield_waves_spawn_expected_mine_counts() -> None:
    game = make_game()
    player = Vector(140.0, 260.0)

    game._wave_count = 7
    _, early_mines = game._spawn_wave(8.1, player)
    assert len(early_mines) == 1
    assert early_mines[0].position.y == player.y

    game._wave_count = 11
    _, late_mines = game._spawn_wave(30.1, player)
    assert len(late_mines) == 2
    assert any(mine.position.y == player.y for mine in late_mines)
    assert any(mine.position.y != player.y for mine in late_mines)


def test_drone_moves_straight_left() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    enemy = Enemy(
        kind=EnemyKind.DRONE,
        position=Vector(500.0, 220.0),
        base_y=220.0,
        age=0.0,
        phase=0.0,
        fire_timer=1.0,
        burst_shots_remaining=0,
        burst_timer=0.0,
    )
    game.state = replace(game.state, enemies=(enemy,))

    game.step(0.5)

    assert game.state.enemies[0].position.x < 500.0
    assert game.state.enemies[0].position.y == 220.0


def test_swooper_oscillates_while_moving_left() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    enemy = Enemy(
        kind=EnemyKind.SWOOPER,
        position=Vector(500.0, 220.0),
        base_y=220.0,
        age=0.0,
        phase=0.0,
        fire_timer=1.0,
        burst_shots_remaining=0,
        burst_timer=0.0,
    )
    game.state = replace(game.state, enemies=(enemy,))

    game.step(0.25)

    assert game.state.enemies[0].position.x < 500.0
    assert game.state.enemies[0].position.y > 220.0


def test_gunship_unlocks_earlier_and_fires_aimed_bursts() -> None:
    game = make_game()

    game.state = replace(game.state, elapsed_time=24.0)
    assert game.available_enemy_kinds == (
        EnemyKind.DRONE,
        EnemyKind.SWOOPER,
        EnemyKind.GUNSHIP,
    )

    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    player = Vector(120.0, 280.0)
    enemy = Enemy(
        kind=EnemyKind.GUNSHIP,
        position=Vector(460.0, 160.0),
        base_y=160.0,
        age=0.0,
        phase=0.0,
        fire_timer=0.01,
        burst_shots_remaining=0,
        burst_timer=0.0,
    )
    game.state = replace(game.state, player_position=player, enemies=(enemy,))

    game.step(0.02)

    assert len(game.state.enemy_projectiles) == 1
    first_shot = game.state.enemy_projectiles[0]
    assert first_shot.velocity.x < 0.0
    assert first_shot.velocity.y > 0.0

    game.step(0.12)

    assert len(game.state.enemy_projectiles) == 2


def test_destroying_seventh_enemy_scores_and_spawns_weapon_pickup() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    enemy = Enemy(
        kind=EnemyKind.DRONE,
        position=Vector(360.0, 230.0),
        base_y=230.0,
        age=0.0,
        phase=0.0,
        fire_timer=1.0,
        burst_shots_remaining=0,
        burst_timer=0.0,
    )
    projectile = Projectile(
        position=enemy.position,
        velocity=Vector(PLAYER_RADIUS, 0.0),
        radius=6.0,
    )
    game.state = replace(game.state, enemies=(enemy,), player_projectiles=(projectile,), kills=6)

    game.step(1.0 / 120.0)

    assert game.state.score == DRONE_SCORE
    assert game.state.kills == 7
    assert len(game.state.pickups) == 1
    assert game.state.pickups[0].kind is PickupType.WEAPON


def test_pickup_cycle_rotates_weapon_shield_score() -> None:
    assert pickup_for_kill_count(7) is PickupType.WEAPON
    assert pickup_for_kill_count(14) is PickupType.SHIELD
    assert pickup_for_kill_count(21) is PickupType.SCORE


def test_collecting_pickups_upgrades_ship_and_awards_bonuses() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    player = game.state.player_position
    pickups = (
        Pickup(PickupType.WEAPON, player, player.y, 0.0),
        Pickup(PickupType.SHIELD, player, player.y, 0.0),
    )
    game.state = replace(game.state, pickups=pickups, shields=2, weapon_level=1)

    game.step(1.0 / 120.0)

    assert game.state.weapon_level == 2
    assert game.state.shields == 3

    game.state = replace(
        game.state,
        pickups=(
            Pickup(PickupType.SHIELD, player, player.y, 0.0),
            Pickup(PickupType.SCORE, player, player.y, 0.0),
        ),
        shields=MAX_SHIELDS,
        score=0,
    )

    game.step(1.0 / 120.0)

    assert game.state.score == FULL_SHIELD_SCORE_BONUS + PICKUP_SCORE_BONUS


def test_player_shots_do_not_remove_mines() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    mine = Mine(position=Vector(360.0, 240.0), ttl=4.0, pulse=0.0)
    projectile = Projectile(position=mine.position, velocity=Vector(0.0, 0.0), radius=6.0)
    game.state = replace(game.state, mines=(mine,), player_projectiles=(projectile,))

    game.step(1.0 / 120.0)

    assert len(game.state.mines) == 1


def test_mines_drift_left_and_damage_on_contact() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    drifting_mine = Mine(position=Vector(400.0, 220.0), ttl=0.2, pulse=0.0)
    game.state = replace(game.state, mines=(drifting_mine,))

    game.step(0.05)

    assert game.state.mines[0].position.x < 400.0

    contact_mine = Mine(position=game.state.player_position, ttl=4.0, pulse=0.0)
    game.state = replace(game.state, mines=(contact_mine,), shields=MAX_SHIELDS)

    game.step(1.0 / 120.0)

    assert game.state.shields == MAX_SHIELDS - 1
    assert game.state.mines == ()


def test_damage_grants_invulnerability_and_prevents_chain_hits() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    player = game.state.player_position
    projectiles = (
        Projectile(player, Vector(-ENEMY_PROJECTILE_SPEED, 0.0), ENEMY_PROJECTILE_RADIUS),
        Projectile(player, Vector(-ENEMY_PROJECTILE_SPEED, 0.0), ENEMY_PROJECTILE_RADIUS),
    )
    game.state = replace(game.state, enemy_projectiles=projectiles)

    game.step(1.0 / 120.0)

    assert game.state.shields == MAX_SHIELDS - 1
    assert game.state.invulnerability_timer > 0.0
    assert game.state.enemy_projectiles == ()

    game.state = replace(
        game.state,
        enemy_projectiles=(
            Projectile(player, Vector(-ENEMY_PROJECTILE_SPEED, 0.0), ENEMY_PROJECTILE_RADIUS),
        ),
    )

    game.step(1.0 / 120.0)

    assert game.state.shields == MAX_SHIELDS - 1


def test_difficulty_progression_unlocks_enemy_types_and_faster_pacing() -> None:
    game = make_game()

    assert game.available_enemy_kinds == (EnemyKind.DRONE,)

    game.state = replace(game.state, elapsed_time=12.0)
    assert game.available_enemy_kinds == (EnemyKind.DRONE, EnemyKind.SWOOPER)

    game.state = replace(game.state, elapsed_time=24.0)
    assert game.available_enemy_kinds == (
        EnemyKind.DRONE,
        EnemyKind.SWOOPER,
        EnemyKind.GUNSHIP,
    )

    game.state = replace(game.state, elapsed_time=60.0)
    assert game.current_scroll_speed == 196.0
    assert game.current_spawn_interval == pytest.approx(0.8)


def test_stationary_runs_now_fail_well_before_the_old_safe_window() -> None:
    survivals: list[float] = []
    for seed in range(6):
        game = make_game(seed)
        delta_seconds = 1.0 / 120.0
        for _ in range(120 * 120):
            if game.state.phase is StarfighterPhase.LOST:
                break
            game.step(delta_seconds)
        survivals.append(game.state.elapsed_time)

    assert max(survivals) < 70.0


def test_losing_last_shield_ends_the_run() -> None:
    game = make_game()
    game._auto_fire_timer = 999.0
    game._spawn_timer = 999.0
    player = game.state.player_position
    projectile = Projectile(player, Vector(-ENEMY_PROJECTILE_SPEED, 0.0), ENEMY_PROJECTILE_RADIUS)
    game.state = replace(game.state, shields=1, enemy_projectiles=(projectile,))

    game.step(1.0 / 120.0)

    assert game.state.phase is StarfighterPhase.LOST
    assert game.state.shields == 0
    assert game.last_events[-1].kind == "player_hit"


def test_enemy_scores_match_their_kind_values() -> None:
    assert DRONE_SCORE < SWOOPER_SCORE < GUNSHIP_SCORE
    assert MINE_RADIUS > 0.0
