from __future__ import annotations

import random

from minigame_collection.games.snake import Direction, Point, SnakeGame, SnakeState


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


def test_step_moves_head_and_body_forward() -> None:
    game = SnakeGame(10, 10, rng=random.Random(0))
    original_body = game.state.body

    game.step()

    assert game.state.body[0] == Point(original_body[0].x + 1, original_body[0].y)
    assert game.state.body[1] == original_body[0]
    assert game.state.body[2] == original_body[1]


def test_reverse_input_is_ignored_for_longer_snake() -> None:
    game = SnakeGame(10, 10, rng=random.Random(0))

    game.request_direction(Direction.LEFT)
    game.step()

    assert game.state.direction is Direction.RIGHT
    assert game.state.body[0] == Point(6, 5)


def test_food_never_spawns_on_the_snake() -> None:
    game = SnakeGame(10, 10, rng=random.Random(3))

    assert game.state.food is not None
    assert game.state.food not in game.state.body


def test_eating_food_increases_score_and_length() -> None:
    game = SnakeGame(10, 10, rng=random.Random(1))
    game.state = make_state(
        body=(Point(5, 5), Point(4, 5), Point(3, 5)),
        direction=Direction.RIGHT,
        food=Point(6, 5),
    )

    game.step()

    assert game.state.score == 1
    assert len(game.state.body) == 4
    assert game.state.body[0] == Point(6, 5)


def test_wall_collision_ends_the_run() -> None:
    game = SnakeGame(10, 10, rng=random.Random(2))
    game.state = make_state(
        body=(Point(9, 4), Point(8, 4), Point(7, 4)),
        direction=Direction.RIGHT,
        food=Point(0, 0),
    )

    game.step()

    assert game.state.alive is False


def test_self_collision_ends_the_run() -> None:
    game = SnakeGame(10, 10, rng=random.Random(2))
    game.state = make_state(
        body=(
            Point(5, 5),
            Point(5, 6),
            Point(4, 6),
            Point(4, 5),
            Point(4, 4),
        ),
        direction=Direction.UP,
        pending_direction=Direction.LEFT,
        food=Point(8, 8),
    )

    game.step()

    assert game.state.alive is False


def test_reset_restores_starting_state() -> None:
    game = SnakeGame(10, 10, rng=random.Random(7))
    game.state = make_state(
        body=(Point(8, 5), Point(7, 5), Point(6, 5), Point(5, 5)),
        direction=Direction.RIGHT,
        pending_direction=Direction.RIGHT,
        food=Point(9, 5),
        score=6,
        alive=False,
    )

    game.reset()

    assert game.state.alive is True
    assert game.state.score == 0
    assert len(game.state.body) == 3
    assert game.state.direction is Direction.RIGHT
    assert game.state.pending_direction is Direction.RIGHT
    assert game.state.food is not None
    assert game.state.food not in game.state.body
