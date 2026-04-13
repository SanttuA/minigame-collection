from __future__ import annotations

import random
from dataclasses import dataclass, replace


BOARD_COLUMNS = 10
BOARD_ROWS = 20
LINE_CLEAR_SCORES = {
    1: 100,
    2: 300,
    3: 500,
    4: 800,
}
WALL_KICK_OFFSETS = (0, -1, 1, -2, 2)
PIECE_KINDS = ("I", "J", "L", "O", "S", "T", "Z")


@dataclass(frozen=True, slots=True)
class GridPoint:
    x: int
    y: int

    def translated(self, dx: int = 0, dy: int = 0) -> "GridPoint":
        return GridPoint(self.x + dx, self.y + dy)


@dataclass(frozen=True, slots=True)
class FallingPiece:
    kind: str
    rotation: int
    position: GridPoint


BoardCell = str | None
BoardRow = tuple[BoardCell, ...]
Board = tuple[BoardRow, ...]


@dataclass(frozen=True, slots=True)
class BlockfallState:
    board: Board
    active_piece: FallingPiece | None
    next_kind: str
    score: int
    lines_cleared: int
    level: int
    alive: bool


PIECE_ROTATIONS: dict[str, tuple[tuple[GridPoint, ...], ...]] = {
    "I": (
        (GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1), GridPoint(3, 1)),
        (GridPoint(2, 0), GridPoint(2, 1), GridPoint(2, 2), GridPoint(2, 3)),
        (GridPoint(0, 2), GridPoint(1, 2), GridPoint(2, 2), GridPoint(3, 2)),
        (GridPoint(1, 0), GridPoint(1, 1), GridPoint(1, 2), GridPoint(1, 3)),
    ),
    "J": (
        (GridPoint(0, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(1, 1), GridPoint(1, 2)),
        (GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1), GridPoint(2, 2)),
        (GridPoint(1, 0), GridPoint(1, 1), GridPoint(0, 2), GridPoint(1, 2)),
    ),
    "L": (
        (GridPoint(2, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(1, 1), GridPoint(1, 2), GridPoint(2, 2)),
        (GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1), GridPoint(0, 2)),
        (GridPoint(0, 0), GridPoint(1, 0), GridPoint(1, 1), GridPoint(1, 2)),
    ),
    "O": (
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(1, 1), GridPoint(2, 1)),
    ),
    "S": (
        (GridPoint(1, 0), GridPoint(2, 0), GridPoint(0, 1), GridPoint(1, 1)),
        (GridPoint(1, 0), GridPoint(1, 1), GridPoint(2, 1), GridPoint(2, 2)),
        (GridPoint(1, 1), GridPoint(2, 1), GridPoint(0, 2), GridPoint(1, 2)),
        (GridPoint(0, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(1, 2)),
    ),
    "T": (
        (GridPoint(1, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(1, 0), GridPoint(1, 1), GridPoint(2, 1), GridPoint(1, 2)),
        (GridPoint(0, 1), GridPoint(1, 1), GridPoint(2, 1), GridPoint(1, 2)),
        (GridPoint(1, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(1, 2)),
    ),
    "Z": (
        (GridPoint(0, 0), GridPoint(1, 0), GridPoint(1, 1), GridPoint(2, 1)),
        (GridPoint(2, 0), GridPoint(1, 1), GridPoint(2, 1), GridPoint(1, 2)),
        (GridPoint(0, 1), GridPoint(1, 1), GridPoint(1, 2), GridPoint(2, 2)),
        (GridPoint(1, 0), GridPoint(0, 1), GridPoint(1, 1), GridPoint(0, 2)),
    ),
}


def empty_board(
    columns: int = BOARD_COLUMNS,
    rows: int = BOARD_ROWS,
) -> Board:
    empty_row = tuple(None for _ in range(columns))
    return tuple(empty_row for _ in range(rows))


def piece_cells(piece: FallingPiece) -> tuple[GridPoint, ...]:
    return tuple(
        piece.position.translated(offset.x, offset.y)
        for offset in PIECE_ROTATIONS[piece.kind][piece.rotation]
    )


class BlockfallGame:
    def __init__(
        self,
        columns: int = BOARD_COLUMNS,
        rows: int = BOARD_ROWS,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.columns = columns
        self.rows = rows
        self._rng = rng or random.Random()
        self._queue: list[str] = []
        self.state = self._build_initial_state()

    def reset(self) -> None:
        self._queue = []
        self.state = self._build_initial_state()

    def move_horizontal(self, delta: int) -> None:
        if delta == 0 or not self.state.alive or self.state.active_piece is None:
            return

        candidate = replace(
            self.state.active_piece,
            position=self.state.active_piece.position.translated(dx=delta),
        )
        if self._piece_fits(candidate):
            self.state = replace(self.state, active_piece=candidate)

    def rotate_clockwise(self) -> None:
        if not self.state.alive or self.state.active_piece is None:
            return

        rotated = replace(
            self.state.active_piece,
            rotation=(self.state.active_piece.rotation + 1) % 4,
        )
        for offset in WALL_KICK_OFFSETS:
            candidate = replace(
                rotated,
                position=rotated.position.translated(dx=offset),
            )
            if self._piece_fits(candidate):
                self.state = replace(self.state, active_piece=candidate)
                return

    def soft_drop(self) -> None:
        self._advance_downward()

    def step(self) -> None:
        self._advance_downward()

    def _build_initial_state(self) -> BlockfallState:
        board = empty_board(self.columns, self.rows)
        active_piece = self._spawn_piece(self._draw_kind())
        next_kind = self._draw_kind()
        return BlockfallState(
            board=board,
            active_piece=active_piece,
            next_kind=next_kind,
            score=0,
            lines_cleared=0,
            level=0,
            alive=self._piece_fits(active_piece, board),
        )

    def _advance_downward(self) -> None:
        if not self.state.alive or self.state.active_piece is None:
            return

        candidate = replace(
            self.state.active_piece,
            position=self.state.active_piece.position.translated(dy=1),
        )
        if self._piece_fits(candidate):
            self.state = replace(self.state, active_piece=candidate)
            return

        locked_board = self._lock_piece(self.state.board, self.state.active_piece)
        cleared_board, cleared_lines = self._clear_full_rows(locked_board)
        total_lines = self.state.lines_cleared + cleared_lines
        level = total_lines // 10
        score = self.state.score
        if cleared_lines:
            score += LINE_CLEAR_SCORES[cleared_lines] * (level + 1)

        next_piece = self._spawn_piece(self.state.next_kind)
        next_kind = self._draw_kind()
        if not self._piece_fits(next_piece, cleared_board):
            self.state = BlockfallState(
                board=cleared_board,
                active_piece=None,
                next_kind=next_kind,
                score=score,
                lines_cleared=total_lines,
                level=level,
                alive=False,
            )
            return

        self.state = BlockfallState(
            board=cleared_board,
            active_piece=next_piece,
            next_kind=next_kind,
            score=score,
            lines_cleared=total_lines,
            level=level,
            alive=True,
        )

    def _spawn_piece(self, kind: str) -> FallingPiece:
        return FallingPiece(
            kind=kind,
            rotation=0,
            position=GridPoint((self.columns // 2) - 2, 0),
        )

    def _piece_fits(self, piece: FallingPiece, board: Board | None = None) -> bool:
        active_board = self.state.board if board is None else board
        for cell in piece_cells(piece):
            if not (0 <= cell.x < self.columns and 0 <= cell.y < self.rows):
                return False
            if active_board[cell.y][cell.x] is not None:
                return False
        return True

    def _lock_piece(self, board: Board, piece: FallingPiece) -> Board:
        rows = [list(row) for row in board]
        for cell in piece_cells(piece):
            rows[cell.y][cell.x] = piece.kind
        return tuple(tuple(row) for row in rows)

    def _clear_full_rows(self, board: Board) -> tuple[Board, int]:
        kept_rows = [row for row in board if any(cell is None for cell in row)]
        cleared_lines = self.rows - len(kept_rows)
        if cleared_lines == 0:
            return board, 0

        empty_row = tuple(None for _ in range(self.columns))
        new_board = tuple([empty_row] * cleared_lines + kept_rows)
        return new_board, cleared_lines

    def _draw_kind(self) -> str:
        if not self._queue:
            self._queue = list(PIECE_KINDS)
            self._rng.shuffle(self._queue)
        return self._queue.pop()
