from __future__ import annotations

from dataclasses import replace

from minigame_collection.games.breakout.logic import (
    BALL_RADIUS,
    BALL_SPEED,
    BRICK_SCORE,
    INITIAL_LIVES,
    PADDLE_BOTTOM_MARGIN,
    PADDLE_HEIGHT,
    PADDLE_WIDTH,
    BreakoutGame,
    BreakoutPhase,
    Vector,
)

BOARD_WIDTH = 704
BOARD_HEIGHT = 512


def test_initial_state_waits_for_manual_serve() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)

    assert game.state.phase is BreakoutPhase.WAITING
    assert game.state.score == 0
    assert game.state.lives == INITIAL_LIVES
    assert len(game.state.bricks) == 50
    assert game.state.ball_velocity == Vector(0.0, 0.0)


def test_paddle_movement_clamps_to_board_edges() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)

    game.set_paddle_direction(-1)
    game.step(2.0)

    assert game.state.paddle_center_x == PADDLE_WIDTH / 2.0
    assert game.state.ball_position.x == game.state.paddle_center_x


def test_launch_ball_starts_play_from_waiting_state() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)

    game.launch_ball()

    assert game.state.phase is BreakoutPhase.PLAYING
    assert game.state.ball_velocity.x > 0.0
    assert game.state.ball_velocity.y < 0.0


def test_top_wall_collision_reflects_the_ball() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        ball_position=Vector(180.0, BALL_RADIUS + 1.0),
        ball_velocity=Vector(90.0, -BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert game.state.ball_position.y >= BALL_RADIUS
    assert game.state.ball_velocity.y > 0.0


def test_paddle_collision_angles_ball_based_on_hit_offset() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    paddle_top = BOARD_HEIGHT - PADDLE_BOTTOM_MARGIN - PADDLE_HEIGHT
    left_side_hit_x = game.state.paddle_center_x - PADDLE_WIDTH * 0.35
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        ball_position=Vector(left_side_hit_x, paddle_top - BALL_RADIUS - 1.0),
        ball_velocity=Vector(0.0, BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert game.state.ball_velocity.y < 0.0
    assert game.state.ball_velocity.x < 0.0


def test_breaking_a_brick_increases_score_and_removes_it() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    target_brick = game.state.bricks[0]
    spare_brick = game.state.bricks[1]
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        bricks=(target_brick, spare_brick),
        ball_position=Vector(
            target_brick.x + target_brick.width / 2.0,
            target_brick.bottom + BALL_RADIUS + 1.0,
        ),
        ball_velocity=Vector(0.0, -BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert len(game.state.bricks) == 1
    assert target_brick not in game.state.bricks
    assert game.state.score == BRICK_SCORE
    assert game.state.phase is BreakoutPhase.PLAYING


def test_missing_the_ball_spends_a_life_and_resets_to_waiting() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    original_bricks = game.state.bricks[:3]
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        bricks=original_bricks,
        score=250,
        ball_position=Vector(240.0, BOARD_HEIGHT + BALL_RADIUS + 1.0),
        ball_velocity=Vector(0.0, BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert game.state.phase is BreakoutPhase.WAITING
    assert game.state.lives == INITIAL_LIVES - 1
    assert game.state.score == 250
    assert game.state.bricks == original_bricks
    assert game.state.ball_velocity == Vector(0.0, 0.0)


def test_breaking_the_last_brick_wins_the_round() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    target_brick = game.state.bricks[0]
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        bricks=(target_brick,),
        ball_position=Vector(
            target_brick.x + target_brick.width / 2.0,
            target_brick.bottom + BALL_RADIUS + 1.0,
        ),
        ball_velocity=Vector(0.0, -BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert game.state.phase is BreakoutPhase.WON
    assert game.state.score == BRICK_SCORE
    assert game.state.bricks == ()


def test_missing_the_last_life_ends_the_run() -> None:
    game = BreakoutGame(BOARD_WIDTH, BOARD_HEIGHT)
    game.state = replace(
        game.state,
        phase=BreakoutPhase.PLAYING,
        lives=1,
        ball_position=Vector(240.0, BOARD_HEIGHT + BALL_RADIUS + 1.0),
        ball_velocity=Vector(0.0, BALL_SPEED),
    )

    game.step(1.0 / 120.0)

    assert game.state.phase is BreakoutPhase.LOST
    assert game.state.lives == 0
    assert game.state.ball_velocity == Vector(0.0, 0.0)
