from __future__ import annotations

import random

from minigame_collection.games.blockfall import (
    BOARD_COLUMNS,
    BOARD_ROWS,
    BlockfallGame,
    BlockfallState,
    FallingPiece,
    GridPoint,
    empty_board,
)


def make_state(
    *,
    board=None,
    active_piece: FallingPiece | None,
    next_kind: str = "I",
    score: int = 0,
    lines_cleared: int = 0,
    level: int = 0,
    alive: bool = True,
) -> BlockfallState:
    return BlockfallState(
        board=board or empty_board(),
        active_piece=active_piece,
        next_kind=next_kind,
        score=score,
        lines_cleared=lines_cleared,
        level=level,
        alive=alive,
    )


def board_with_cells(*cells: tuple[int, int, str]) -> tuple[tuple[str | None, ...], ...]:
    rows = [list(row) for row in empty_board()]
    for x, y, kind in cells:
        rows[y][x] = kind
    return tuple(tuple(row) for row in rows)


def test_initial_state_spawns_piece_and_preview() -> None:
    game = BlockfallGame(rng=random.Random(0))

    assert game.state.active_piece is not None
    assert game.state.active_piece.kind in {"I", "J", "L", "O", "S", "T", "Z"}
    assert game.state.next_kind in {"I", "J", "L", "O", "S", "T", "Z"}
    assert game.state.alive is True


def test_horizontal_movement_respects_bounds_and_settled_blocks() -> None:
    game = BlockfallGame(rng=random.Random(1))
    game.state = make_state(
        active_piece=FallingPiece("O", 0, GridPoint(-1, 0)),
        next_kind="I",
    )

    game.move_horizontal(-1)

    assert game.state.active_piece == FallingPiece("O", 0, GridPoint(-1, 0))

    game.state = make_state(
        board=board_with_cells((6, 0, "J")),
        active_piece=FallingPiece("O", 0, GridPoint(3, 0)),
        next_kind="I",
    )

    game.move_horizontal(1)

    assert game.state.active_piece == FallingPiece("O", 0, GridPoint(3, 0))


def test_rotation_uses_wall_kick_near_edges() -> None:
    game = BlockfallGame(rng=random.Random(2))
    game.state = make_state(
        active_piece=FallingPiece("I", 1, GridPoint(-2, 0)),
        next_kind="O",
    )

    game.rotate_clockwise()

    assert game.state.active_piece == FallingPiece("I", 2, GridPoint(0, 0))


def test_clearing_a_line_updates_score_lines_and_level() -> None:
    bottom_y = BOARD_ROWS - 1
    almost_full_bottom = tuple(
        None if column in {4, 5} else "Z" for column in range(BOARD_COLUMNS)
    )
    rows = [list(row) for row in empty_board()]
    rows[bottom_y] = list(almost_full_bottom)

    game = BlockfallGame(rng=random.Random(3))
    game.state = make_state(
        board=tuple(tuple(row) for row in rows),
        active_piece=FallingPiece("O", 0, GridPoint(3, BOARD_ROWS - 2)),
        next_kind="T",
        lines_cleared=9,
    )

    game.step()

    assert game.state.score == 200
    assert game.state.lines_cleared == 10
    assert game.state.level == 1
    assert game.state.active_piece is not None
    assert game.state.active_piece.kind == "T"


def test_blocked_downward_step_locks_piece_and_spawns_next_piece() -> None:
    game = BlockfallGame(rng=random.Random(4))
    game.state = make_state(
        active_piece=FallingPiece("O", 0, GridPoint(3, BOARD_ROWS - 2)),
        next_kind="I",
    )

    game.step()

    assert game.state.active_piece is not None
    assert game.state.active_piece.kind == "I"
    assert game.state.board[BOARD_ROWS - 1][4] == "O"
    assert game.state.board[BOARD_ROWS - 1][5] == "O"


def test_spawn_collision_ends_the_run() -> None:
    game = BlockfallGame(rng=random.Random(5))
    game.state = make_state(
        board=board_with_cells((4, 0, "L")),
        active_piece=FallingPiece("O", 0, GridPoint(3, 18)),
        next_kind="O",
    )

    game.step()

    assert game.state.alive is False
    assert game.state.active_piece is None


def test_reset_restores_a_fresh_state() -> None:
    game = BlockfallGame(rng=random.Random(6))
    game.state = make_state(
        board=board_with_cells((0, 0, "S"), (1, 0, "S")),
        active_piece=None,
        next_kind="J",
        score=1200,
        lines_cleared=14,
        level=1,
        alive=False,
    )

    game.reset()

    assert game.state.alive is True
    assert game.state.score == 0
    assert game.state.lines_cleared == 0
    assert game.state.level == 0
    assert game.state.active_piece is not None
    assert all(cell is None for row in game.state.board for cell in row)
