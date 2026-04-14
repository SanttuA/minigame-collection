from __future__ import annotations

import math
from dataclasses import dataclass, replace
from enum import Enum


BRICK_COLUMNS = 10
BRICK_ROWS = 5
BRICK_GAP_X = 8.0
BRICK_GAP_Y = 10.0
BRICK_SIDE_MARGIN = 24.0
BRICK_TOP_MARGIN = 36.0
BRICK_HEIGHT = 24.0
BRICK_SCORE = 100
INITIAL_LIVES = 3
PADDLE_WIDTH = 112.0
PADDLE_HEIGHT = 16.0
PADDLE_BOTTOM_MARGIN = 22.0
PADDLE_SPEED = 480.0
BALL_RADIUS = 8.0
BALL_SPEED = 360.0
BALL_ATTACH_GAP = 6.0
MAX_BOUNCE_ANGLE = math.radians(60)
LAUNCH_ANGLE = math.radians(30)


@dataclass(frozen=True, slots=True)
class Vector:
    x: float
    y: float

    def translated(self, *, dx: float = 0.0, dy: float = 0.0) -> "Vector":
        return Vector(self.x + dx, self.y + dy)


class BreakoutPhase(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class Brick:
    row: int
    column: int
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> Vector:
        return Vector(self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass(frozen=True, slots=True)
class BreakoutState:
    paddle_center_x: float
    paddle_direction: int
    ball_position: Vector
    ball_velocity: Vector
    bricks: tuple[Brick, ...]
    score: int
    lives: int
    phase: BreakoutPhase


class BreakoutGame:
    def __init__(self, board_width: float, board_height: float) -> None:
        self.board_width = board_width
        self.board_height = board_height
        self._brick_width = (
            board_width
            - BRICK_SIDE_MARGIN * 2.0
            - BRICK_GAP_X * (BRICK_COLUMNS - 1)
        ) / BRICK_COLUMNS
        self._paddle_top = board_height - PADDLE_BOTTOM_MARGIN - PADDLE_HEIGHT
        self.state = self._build_initial_state()

    def reset(self) -> None:
        self.state = self._build_initial_state()

    def set_paddle_direction(self, direction: int) -> None:
        if self.state.phase in (BreakoutPhase.WON, BreakoutPhase.LOST):
            return

        self.state = replace(self.state, paddle_direction=_clamp_direction(direction))

    def launch_ball(self) -> None:
        if self.state.phase is not BreakoutPhase.WAITING:
            return

        self.state = replace(
            self.state,
            phase=BreakoutPhase.PLAYING,
            ball_velocity=_velocity_from_angle(LAUNCH_ANGLE, BALL_SPEED),
        )

    def step(self, delta_seconds: float) -> None:
        if delta_seconds <= 0.0:
            return

        if self.state.phase in (BreakoutPhase.WON, BreakoutPhase.LOST):
            return

        paddle_center_x = _clamp(
            self.state.paddle_center_x + self.state.paddle_direction * PADDLE_SPEED * delta_seconds,
            minimum=PADDLE_WIDTH / 2.0,
            maximum=self.board_width - PADDLE_WIDTH / 2.0,
        )

        if self.state.phase is BreakoutPhase.WAITING:
            self.state = replace(
                self.state,
                paddle_center_x=paddle_center_x,
                ball_position=self._waiting_ball_position(paddle_center_x),
            )
            return

        previous_ball = self.state.ball_position
        ball_velocity = self.state.ball_velocity
        ball_position = previous_ball.translated(
            dx=ball_velocity.x * delta_seconds,
            dy=ball_velocity.y * delta_seconds,
        )
        ball_position, ball_velocity = self._apply_wall_bounces(ball_position, ball_velocity)

        paddle_collision = self._resolve_paddle_collision(
            previous_ball,
            ball_position,
            ball_velocity,
            paddle_center_x,
        )
        if paddle_collision is not None:
            ball_position, ball_velocity = paddle_collision

        if self._ball_has_fallen_out(ball_position):
            self._lose_life(paddle_center_x, ball_position)
            return

        bricks = self.state.bricks
        score = self.state.score
        phase = BreakoutPhase.PLAYING
        brick_collision = self._resolve_brick_collision(previous_ball, ball_position, ball_velocity)
        if brick_collision is not None:
            hit_brick, ball_position, ball_velocity = brick_collision
            bricks = tuple(brick for brick in bricks if brick != hit_brick)
            score += BRICK_SCORE
            if not bricks:
                phase = BreakoutPhase.WON
                ball_velocity = Vector(0.0, 0.0)

        self.state = BreakoutState(
            paddle_center_x=paddle_center_x,
            paddle_direction=self.state.paddle_direction,
            ball_position=ball_position,
            ball_velocity=ball_velocity,
            bricks=bricks,
            score=score,
            lives=self.state.lives,
            phase=phase,
        )

    def _build_initial_state(self) -> BreakoutState:
        paddle_center_x = self.board_width / 2.0
        return BreakoutState(
            paddle_center_x=paddle_center_x,
            paddle_direction=0,
            ball_position=self._waiting_ball_position(paddle_center_x),
            ball_velocity=Vector(0.0, 0.0),
            bricks=self._build_bricks(),
            score=0,
            lives=INITIAL_LIVES,
            phase=BreakoutPhase.WAITING,
        )

    def _build_bricks(self) -> tuple[Brick, ...]:
        bricks: list[Brick] = []
        for row in range(BRICK_ROWS):
            for column in range(BRICK_COLUMNS):
                bricks.append(
                    Brick(
                        row=row,
                        column=column,
                        x=BRICK_SIDE_MARGIN + column * (self._brick_width + BRICK_GAP_X),
                        y=BRICK_TOP_MARGIN + row * (BRICK_HEIGHT + BRICK_GAP_Y),
                        width=self._brick_width,
                        height=BRICK_HEIGHT,
                    )
                )
        return tuple(bricks)

    def _waiting_ball_position(self, paddle_center_x: float) -> Vector:
        return Vector(
            paddle_center_x,
            self._paddle_top - BALL_RADIUS - BALL_ATTACH_GAP,
        )

    def _apply_wall_bounces(
        self,
        ball_position: Vector,
        ball_velocity: Vector,
    ) -> tuple[Vector, Vector]:
        x = ball_position.x
        y = ball_position.y
        vx = ball_velocity.x
        vy = ball_velocity.y

        if x - BALL_RADIUS <= 0.0:
            x = BALL_RADIUS
            vx = abs(vx)
        elif x + BALL_RADIUS >= self.board_width:
            x = self.board_width - BALL_RADIUS
            vx = -abs(vx)

        if y - BALL_RADIUS <= 0.0:
            y = BALL_RADIUS
            vy = abs(vy)

        return Vector(x, y), Vector(vx, vy)

    def _resolve_paddle_collision(
        self,
        previous_ball: Vector,
        ball_position: Vector,
        ball_velocity: Vector,
        paddle_center_x: float,
    ) -> tuple[Vector, Vector] | None:
        if ball_velocity.y <= 0.0:
            return None

        paddle_left = paddle_center_x - PADDLE_WIDTH / 2.0
        paddle_right = paddle_center_x + PADDLE_WIDTH / 2.0
        paddle_bottom = self._paddle_top + PADDLE_HEIGHT
        ball_left = ball_position.x - BALL_RADIUS
        ball_right = ball_position.x + BALL_RADIUS
        ball_top = ball_position.y - BALL_RADIUS
        ball_bottom = ball_position.y + BALL_RADIUS

        if previous_ball.y + BALL_RADIUS > self._paddle_top:
            return None
        if ball_bottom < self._paddle_top or ball_top > paddle_bottom:
            return None
        if ball_right < paddle_left or ball_left > paddle_right:
            return None

        collision_x = _clamp(
            ball_position.x,
            minimum=paddle_left + BALL_RADIUS,
            maximum=paddle_right - BALL_RADIUS,
        )
        offset = (collision_x - paddle_center_x) / (PADDLE_WIDTH / 2.0)
        bounce_angle = offset * MAX_BOUNCE_ANGLE
        return (
            Vector(collision_x, self._paddle_top - BALL_RADIUS),
            _velocity_from_angle(bounce_angle, BALL_SPEED),
        )

    def _ball_has_fallen_out(self, ball_position: Vector) -> bool:
        return ball_position.y - BALL_RADIUS > self.board_height

    def _lose_life(self, paddle_center_x: float, ball_position: Vector) -> None:
        remaining_lives = max(0, self.state.lives - 1)
        next_phase = BreakoutPhase.WAITING if remaining_lives > 0 else BreakoutPhase.LOST
        next_ball_position = (
            self._waiting_ball_position(paddle_center_x)
            if remaining_lives > 0
            else ball_position
        )
        self.state = BreakoutState(
            paddle_center_x=paddle_center_x,
            paddle_direction=self.state.paddle_direction,
            ball_position=next_ball_position,
            ball_velocity=Vector(0.0, 0.0),
            bricks=self.state.bricks,
            score=self.state.score,
            lives=remaining_lives,
            phase=next_phase,
        )

    def _resolve_brick_collision(
        self,
        previous_ball: Vector,
        ball_position: Vector,
        ball_velocity: Vector,
    ) -> tuple[Brick, Vector, Vector] | None:
        hit_bricks = [
            brick
            for brick in self.state.bricks
            if _rects_intersect(
                ball_position.x - BALL_RADIUS,
                ball_position.y - BALL_RADIUS,
                BALL_RADIUS * 2.0,
                BALL_RADIUS * 2.0,
                brick.x,
                brick.y,
                brick.width,
                brick.height,
            )
        ]
        if not hit_bricks:
            return None

        hit_brick = min(
            hit_bricks,
            key=lambda brick: (
                _distance_squared(previous_ball, brick.center),
                brick.row,
                brick.column,
            ),
        )
        axis = self._collision_axis(previous_ball, ball_position, hit_brick)
        if axis == "horizontal":
            return (
                hit_brick,
                Vector(previous_ball.x, ball_position.y),
                Vector(-ball_velocity.x, ball_velocity.y),
            )
        return (
            hit_brick,
            Vector(ball_position.x, previous_ball.y),
            Vector(ball_velocity.x, -ball_velocity.y),
        )

    def _collision_axis(
        self,
        previous_ball: Vector,
        ball_position: Vector,
        brick: Brick,
    ) -> str:
        previous_left = previous_ball.x - BALL_RADIUS
        previous_right = previous_ball.x + BALL_RADIUS
        previous_top = previous_ball.y - BALL_RADIUS
        previous_bottom = previous_ball.y + BALL_RADIUS
        current_left = ball_position.x - BALL_RADIUS
        current_right = ball_position.x + BALL_RADIUS
        current_top = ball_position.y - BALL_RADIUS
        current_bottom = ball_position.y + BALL_RADIUS

        crossed_horizontal = (
            previous_right <= brick.x <= current_right
            or previous_left >= brick.right >= current_left
        )
        crossed_vertical = (
            previous_bottom <= brick.y <= current_bottom
            or previous_top >= brick.bottom >= current_top
        )

        if crossed_horizontal and not crossed_vertical:
            return "horizontal"
        if crossed_vertical and not crossed_horizontal:
            return "vertical"

        overlap_x = min(current_right, brick.right) - max(current_left, brick.x)
        overlap_y = min(current_bottom, brick.bottom) - max(current_top, brick.y)
        if overlap_x < overlap_y:
            return "horizontal"
        return "vertical"


def _velocity_from_angle(angle: float, speed: float) -> Vector:
    return Vector(speed * math.sin(angle), -speed * math.cos(angle))


def _distance_squared(left: Vector, right: Vector) -> float:
    dx = left.x - right.x
    dy = left.y - right.y
    return dx * dx + dy * dy


def _clamp(value: float, *, minimum: float, maximum: float) -> float:
    return min(max(value, minimum), maximum)


def _clamp_direction(direction: int) -> int:
    return max(-1, min(1, direction))


def _rects_intersect(
    left_a: float,
    top_a: float,
    width_a: float,
    height_a: float,
    left_b: float,
    top_b: float,
    width_b: float,
    height_b: float,
) -> bool:
    return (
        left_a < left_b + width_b
        and left_a + width_a > left_b
        and top_a < top_b + height_b
        and top_a + height_a > top_b
    )
