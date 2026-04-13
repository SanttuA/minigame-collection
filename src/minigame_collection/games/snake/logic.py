from __future__ import annotations

import random
from dataclasses import dataclass, replace
from enum import Enum


@dataclass(frozen=True, slots=True)
class Point:
    x: int
    y: int

    def translated(self, direction: "Direction") -> "Point":
        dx, dy = direction.vector
        return Point(self.x + dx, self.y + dy)


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def vector(self) -> tuple[int, int]:
        return self.value

    def opposite(self) -> "Direction":
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposites[self]


@dataclass(frozen=True, slots=True)
class SnakeState:
    body: tuple[Point, ...]
    direction: Direction
    pending_direction: Direction
    food: Point | None
    score: int
    alive: bool


class SnakeGame:
    def __init__(
        self,
        grid_columns: int,
        grid_rows: int,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.grid_columns = grid_columns
        self.grid_rows = grid_rows
        self._rng = rng or random.Random()
        self.state = self._build_initial_state()

    def _build_initial_state(self) -> SnakeState:
        start_x = self.grid_columns // 2
        start_y = self.grid_rows // 2
        body = (
            Point(start_x, start_y),
            Point(start_x - 1, start_y),
            Point(start_x - 2, start_y),
        )
        food = self._spawn_food(body)
        return SnakeState(
            body=body,
            direction=Direction.RIGHT,
            pending_direction=Direction.RIGHT,
            food=food,
            score=0,
            alive=True,
        )

    def reset(self) -> None:
        self.state = self._build_initial_state()

    def request_direction(self, direction: Direction) -> None:
        if not self.state.alive:
            return
        if len(self.state.body) > 1 and direction == self.state.direction.opposite():
            return
        self.state = replace(self.state, pending_direction=direction)

    def step(self) -> None:
        if not self.state.alive:
            return

        direction = self.state.pending_direction
        if len(self.state.body) > 1 and direction == self.state.direction.opposite():
            direction = self.state.direction

        body = self.state.body
        new_head = body[0].translated(direction)
        ate_food = new_head == self.state.food
        new_body = (new_head, *body) if ate_food else (new_head, *body[:-1])

        if not self._is_in_bounds(new_head) or new_head in new_body[1:]:
            self.state = SnakeState(
                body=new_body,
                direction=direction,
                pending_direction=direction,
                food=self.state.food,
                score=self.state.score,
                alive=False,
            )
            return

        score = self.state.score + int(ate_food)
        food = self.state.food
        alive = True
        if ate_food:
            food = self._spawn_food(new_body)
            if food is None:
                alive = False

        self.state = SnakeState(
            body=new_body,
            direction=direction,
            pending_direction=direction,
            food=food,
            score=score,
            alive=alive,
        )

    def _is_in_bounds(self, point: Point) -> bool:
        return 0 <= point.x < self.grid_columns and 0 <= point.y < self.grid_rows

    def _spawn_food(self, body: tuple[Point, ...]) -> Point | None:
        free_cells = [
            Point(x, y)
            for y in range(self.grid_rows)
            for x in range(self.grid_columns)
            if Point(x, y) not in body
        ]
        if not free_cells:
            return None
        return self._rng.choice(free_cells)
