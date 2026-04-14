from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum


START_SCROLL_SPEED = 160.0
SCROLL_SPEED_STEP = 12.0
SCROLL_SPEED_STEP_SECONDS = 20.0
MAX_SCROLL_SPEED = 320.0

START_SPAWN_INTERVAL = 1.20
SPAWN_INTERVAL_STEP = 0.08
SPAWN_INTERVAL_STEP_SECONDS = 12.0
MIN_SPAWN_INTERVAL = 0.35

TARGETED_WAVE_START_SECONDS = 6.0
MINEFIELD_START_SECONDS = 8.0
SWOOPER_UNLOCK_SECONDS = 12.0
GUNSHIP_UNLOCK_SECONDS = 24.0
SECOND_MINEFIELD_SECONDS = 30.0
TARGETED_JITTER = 20.0

PLAYER_RADIUS = 18.0
PLAYER_SPEED = 320.0
MAX_SHIELDS = 3
MAX_WEAPON_LEVEL = 3
INVULNERABILITY_DURATION = 1.0

PLAYER_SHOT_RADIUS = 5.0
PLAYER_SHOT_SPEED = 540.0
PLAYER_SHOT_OFFSETS = {
    1: (0.0,),
    2: (0.0,),
    3: (-10.0, 10.0),
}
AUTO_FIRE_INTERVALS = {
    1: 0.18,
    2: 0.12,
    3: 0.12,
}

ENEMY_PROJECTILE_RADIUS = 6.0
ENEMY_PROJECTILE_SPEED = 380.0
GUNSHIP_BURST_INTERVAL = 1.10
GUNSHIP_BURST_SPACING = 0.12
GUNSHIP_FIRE_INITIAL_DELAY = 0.75

MINE_RADIUS = 17.0
MINE_DRIFT_SPEED = 180.0
MINE_TTL_SECONDS = 4.8
MINE_OFFSET_DISTANCE = 84.0

DISTANCE_PIXELS_PER_POINT = 10.0
PICKUP_DROP_EVERY_KILLS = 7
PICKUP_SCORE_BONUS = 250
FULL_SHIELD_SCORE_BONUS = 150

SPAWN_MARGIN = 56.0
SWOOPER_AMPLITUDE = 44.0
SWOOPER_FREQUENCY = 3.2
PICKUP_BOB_AMPLITUDE = 10.0
PICKUP_BOB_FREQUENCY = 4.0

DRONE_SCORE = 40
SWOOPER_SCORE = 70
GUNSHIP_SCORE = 110


@dataclass(frozen=True, slots=True)
class Vector:
    x: float
    y: float

    def translated(self, *, dx: float = 0.0, dy: float = 0.0) -> "Vector":
        return Vector(self.x + dx, self.y + dy)


class EnemyKind(Enum):
    DRONE = "drone"
    SWOOPER = "swooper"
    GUNSHIP = "gunship"


class PickupType(Enum):
    WEAPON = "weapon"
    SHIELD = "shield"
    SCORE = "score"


class StarfighterPhase(Enum):
    PLAYING = "playing"
    LOST = "lost"


@dataclass(frozen=True, slots=True)
class Projectile:
    position: Vector
    velocity: Vector
    radius: float


@dataclass(frozen=True, slots=True)
class Enemy:
    kind: EnemyKind
    position: Vector
    base_y: float
    age: float
    phase: float
    fire_timer: float
    burst_shots_remaining: int
    burst_timer: float


@dataclass(frozen=True, slots=True)
class Pickup:
    kind: PickupType
    position: Vector
    base_y: float
    age: float


@dataclass(frozen=True, slots=True)
class Mine:
    position: Vector
    ttl: float
    pulse: float


@dataclass(frozen=True, slots=True)
class StarfighterEvent:
    kind: str
    position: Vector


@dataclass(frozen=True, slots=True)
class StarfighterState:
    player_position: Vector
    shields: int
    weapon_level: int
    invulnerability_timer: float
    enemies: tuple[Enemy, ...]
    player_projectiles: tuple[Projectile, ...]
    enemy_projectiles: tuple[Projectile, ...]
    pickups: tuple[Pickup, ...]
    mines: tuple[Mine, ...]
    elapsed_time: float
    distance: int
    score: int
    kills: int
    phase: StarfighterPhase


PICKUP_SEQUENCE = (
    PickupType.WEAPON,
    PickupType.SHIELD,
    PickupType.SCORE,
)

FORMATION_PATTERNS = (
    ((0.0, 0.0),),
    ((0.0, -54.0), (48.0, 54.0)),
    ((0.0, 0.0), (58.0, -60.0), (58.0, 60.0)),
    ((0.0, -72.0), (42.0, 0.0), (84.0, 72.0)),
)
PINCH_PATTERN = ((0.0, -68.0), (40.0, 0.0), (0.0, 68.0))


class StarfighterGame:
    def __init__(
        self,
        board_width: float,
        board_height: float,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self.board_width = board_width
        self.board_height = board_height
        self._rng = rng or random.Random()
        self._movement = Vector(0.0, 0.0)
        self._auto_fire_timer = 0.0
        self._spawn_timer = START_SPAWN_INTERVAL
        self._distance_remainder = 0.0
        self._wave_count = 0
        self._last_events: tuple[StarfighterEvent, ...] = ()
        self.state = self._build_initial_state()

    @property
    def current_scroll_speed(self) -> float:
        return scroll_speed_for_elapsed(self.state.elapsed_time)

    @property
    def current_spawn_interval(self) -> float:
        return spawn_interval_for_elapsed(self.state.elapsed_time)

    @property
    def available_enemy_kinds(self) -> tuple[EnemyKind, ...]:
        return available_enemy_kinds_for_elapsed(self.state.elapsed_time)

    @property
    def last_events(self) -> tuple[StarfighterEvent, ...]:
        return self._last_events

    def reset(self) -> None:
        self._movement = Vector(0.0, 0.0)
        self._auto_fire_timer = 0.0
        self._spawn_timer = START_SPAWN_INTERVAL
        self._distance_remainder = 0.0
        self._wave_count = 0
        self._last_events = ()
        self.state = self._build_initial_state()

    def set_movement(self, horizontal: int, vertical: int) -> None:
        if self.state.phase is StarfighterPhase.LOST:
            self._movement = Vector(0.0, 0.0)
            return

        self._movement = Vector(
            float(_clamp_direction(horizontal)),
            float(_clamp_direction(vertical)),
        )

    def step(self, delta_seconds: float) -> tuple[StarfighterEvent, ...]:
        if delta_seconds <= 0.0 or self.state.phase is StarfighterPhase.LOST:
            self._last_events = ()
            return self._last_events

        events: list[StarfighterEvent] = []
        previous_state = self.state
        elapsed_time = previous_state.elapsed_time + delta_seconds
        scroll_speed = scroll_speed_for_elapsed(elapsed_time)
        spawn_interval = spawn_interval_for_elapsed(elapsed_time)

        player_position = self._move_player(previous_state.player_position, delta_seconds)
        distance, score = self._advance_distance(
            previous_state.distance,
            previous_state.score,
            scroll_speed,
            delta_seconds,
        )
        weapon_level = previous_state.weapon_level
        shields = previous_state.shields
        invulnerability = max(0.0, previous_state.invulnerability_timer - delta_seconds)

        player_projectiles = self._advance_projectiles(
            previous_state.player_projectiles,
            delta_seconds,
            min_x=-PLAYER_SHOT_RADIUS,
            max_x=self.board_width + PLAYER_SHOT_RADIUS * 2.0,
        )
        enemy_projectiles = self._advance_projectiles(
            previous_state.enemy_projectiles,
            delta_seconds,
            min_x=-ENEMY_PROJECTILE_RADIUS * 2.0,
            max_x=self.board_width + ENEMY_PROJECTILE_RADIUS,
        )
        pickups = self._advance_pickups(previous_state.pickups, scroll_speed, delta_seconds)
        mines = self._advance_mines(previous_state.mines, scroll_speed, delta_seconds)

        enemies: list[Enemy] = []
        for enemy in previous_state.enemies:
            advanced_enemy, fired_projectiles = self._advance_enemy(
                enemy,
                scroll_speed,
                delta_seconds,
                player_position,
            )
            enemy_projectiles.extend(fired_projectiles)
            if advanced_enemy is not None:
                enemies.append(advanced_enemy)

        self._spawn_timer -= delta_seconds
        while self._spawn_timer <= 0.0:
            spawned_enemies, spawned_mines = self._spawn_wave(elapsed_time, player_position)
            enemies.extend(spawned_enemies)
            mines.extend(spawned_mines)
            self._spawn_timer += spawn_interval

        (
            player_projectiles,
            enemies,
            pickups,
            score,
            kills,
            destroy_events,
        ) = self._resolve_player_projectile_hits(
            player_projectiles,
            enemies,
            pickups,
            score,
            previous_state.kills,
        )
        events.extend(destroy_events)

        pickups, weapon_level, shields, score, pickup_events = self._collect_pickups(
            pickups,
            player_position,
            weapon_level,
            shields,
            score,
        )
        events.extend(pickup_events)

        mines, enemies, enemy_projectiles, shields, invulnerability, damage_events = (
            self._resolve_player_damage(
                mines,
                enemies,
                enemy_projectiles,
                player_position,
                shields,
                invulnerability,
            )
        )
        events.extend(damage_events)

        phase = StarfighterPhase.PLAYING if shields > 0 else StarfighterPhase.LOST
        if phase is StarfighterPhase.PLAYING:
            player_projectiles, weapon_level = self._spawn_auto_fire(
                player_projectiles,
                player_position,
                weapon_level,
                delta_seconds,
            )
        else:
            self._movement = Vector(0.0, 0.0)

        self.state = StarfighterState(
            player_position=player_position,
            shields=shields,
            weapon_level=weapon_level,
            invulnerability_timer=invulnerability,
            enemies=tuple(enemies),
            player_projectiles=tuple(player_projectiles),
            enemy_projectiles=tuple(enemy_projectiles),
            pickups=tuple(pickups),
            mines=tuple(mines),
            elapsed_time=elapsed_time,
            distance=distance,
            score=score,
            kills=kills,
            phase=phase,
        )
        self._last_events = tuple(events)
        return self._last_events

    def _build_initial_state(self) -> StarfighterState:
        return StarfighterState(
            player_position=Vector(self.board_width * 0.18, self.board_height / 2.0),
            shields=MAX_SHIELDS,
            weapon_level=1,
            invulnerability_timer=0.0,
            enemies=(),
            player_projectiles=(),
            enemy_projectiles=(),
            pickups=(),
            mines=(),
            elapsed_time=0.0,
            distance=0,
            score=0,
            kills=0,
            phase=StarfighterPhase.PLAYING,
        )

    def _move_player(self, position: Vector, delta_seconds: float) -> Vector:
        direction = _normalized_vector(self._movement)
        return Vector(
            _clamp(
                position.x + direction.x * PLAYER_SPEED * delta_seconds,
                minimum=PLAYER_RADIUS,
                maximum=self.board_width - PLAYER_RADIUS,
            ),
            _clamp(
                position.y + direction.y * PLAYER_SPEED * delta_seconds,
                minimum=PLAYER_RADIUS,
                maximum=self.board_height - PLAYER_RADIUS,
            ),
        )

    def _advance_distance(
        self,
        distance: int,
        score: int,
        scroll_speed: float,
        delta_seconds: float,
    ) -> tuple[int, int]:
        travelled_pixels = scroll_speed * delta_seconds
        total_pixels = self._distance_remainder + travelled_pixels
        gained_points = int(total_pixels // DISTANCE_PIXELS_PER_POINT)
        self._distance_remainder = total_pixels - gained_points * DISTANCE_PIXELS_PER_POINT
        return distance + gained_points, score + gained_points

    def _advance_projectiles(
        self,
        projectiles: tuple[Projectile, ...],
        delta_seconds: float,
        *,
        min_x: float,
        max_x: float,
    ) -> list[Projectile]:
        advanced: list[Projectile] = []
        for projectile in projectiles:
            position = projectile.position.translated(
                dx=projectile.velocity.x * delta_seconds,
                dy=projectile.velocity.y * delta_seconds,
            )
            if min_x <= position.x <= max_x and -40.0 <= position.y <= self.board_height + 40.0:
                advanced.append(
                    Projectile(
                        position=position,
                        velocity=projectile.velocity,
                        radius=projectile.radius,
                    )
                )
        return advanced

    def _advance_pickups(
        self,
        pickups: tuple[Pickup, ...],
        scroll_speed: float,
        delta_seconds: float,
    ) -> list[Pickup]:
        advanced: list[Pickup] = []
        drift_speed = max(110.0, scroll_speed * 0.85)
        for pickup in pickups:
            age = pickup.age + delta_seconds
            position = Vector(
                pickup.position.x - drift_speed * delta_seconds,
                pickup.base_y + math.sin(age * PICKUP_BOB_FREQUENCY) * PICKUP_BOB_AMPLITUDE,
            )
            if position.x >= -32.0:
                advanced.append(
                    Pickup(
                        kind=pickup.kind,
                        position=position,
                        base_y=pickup.base_y,
                        age=age,
                    )
                )
        return advanced

    def _advance_mines(
        self,
        mines: tuple[Mine, ...],
        scroll_speed: float,
        delta_seconds: float,
    ) -> list[Mine]:
        advanced: list[Mine] = []
        drift_speed = max(MINE_DRIFT_SPEED, scroll_speed * 0.82)
        for mine in mines:
            ttl = mine.ttl - delta_seconds
            position = mine.position.translated(dx=-drift_speed * delta_seconds)
            if ttl > 0.0 and position.x >= -MINE_RADIUS * 2.0:
                advanced.append(Mine(position=position, ttl=ttl, pulse=mine.pulse))
        return advanced

    def _advance_enemy(
        self,
        enemy: Enemy,
        scroll_speed: float,
        delta_seconds: float,
        player_position: Vector,
    ) -> tuple[Enemy | None, list[Projectile]]:
        age = enemy.age + delta_seconds
        x_speed = scroll_speed + enemy_speed_for_kind(enemy.kind)
        position_x = enemy.position.x - x_speed * delta_seconds
        position_y = enemy.base_y
        if enemy.kind is EnemyKind.SWOOPER:
            position_y = enemy.base_y + math.sin(enemy.phase + age * SWOOPER_FREQUENCY) * SWOOPER_AMPLITUDE

        fire_timer = enemy.fire_timer
        burst_shots_remaining = enemy.burst_shots_remaining
        burst_timer = enemy.burst_timer
        spawned_projectiles: list[Projectile] = []

        if enemy.kind is EnemyKind.GUNSHIP:
            if burst_shots_remaining > 0:
                burst_timer -= delta_seconds
                while burst_shots_remaining > 0 and burst_timer <= 0.0:
                    spawned_projectiles.append(
                        Projectile(
                            position=Vector(position_x - 18.0, position_y),
                            velocity=_aimed_velocity(
                                Vector(position_x - 18.0, position_y),
                                player_position,
                                ENEMY_PROJECTILE_SPEED,
                            ),
                            radius=ENEMY_PROJECTILE_RADIUS,
                        )
                    )
                    burst_shots_remaining -= 1
                    burst_timer += GUNSHIP_BURST_SPACING
            else:
                fire_timer -= delta_seconds
                while fire_timer <= 0.0:
                    spawned_projectiles.append(
                        Projectile(
                            position=Vector(position_x - 18.0, position_y),
                            velocity=_aimed_velocity(
                                Vector(position_x - 18.0, position_y),
                                player_position,
                                ENEMY_PROJECTILE_SPEED,
                            ),
                            radius=ENEMY_PROJECTILE_RADIUS,
                        )
                    )
                    fire_timer += GUNSHIP_BURST_INTERVAL
                    burst_shots_remaining = 1
                    burst_timer = GUNSHIP_BURST_SPACING

        position = Vector(position_x, position_y)
        if position_x < -enemy_radius_for_kind(enemy.kind) * 2.0:
            return None, spawned_projectiles

        return (
            Enemy(
                kind=enemy.kind,
                position=position,
                base_y=enemy.base_y,
                age=age,
                phase=enemy.phase,
                fire_timer=fire_timer,
                burst_shots_remaining=burst_shots_remaining,
                burst_timer=burst_timer,
            ),
            spawned_projectiles,
        )

    def _spawn_wave(
        self,
        elapsed_time: float,
        player_position: Vector,
    ) -> tuple[list[Enemy], list[Mine]]:
        tier = difficulty_tier_for_elapsed(elapsed_time)
        wave_number = self._wave_count + 1
        targeted = elapsed_time >= TARGETED_WAVE_START_SECONDS and wave_number % 3 == 0
        minefield = elapsed_time >= MINEFIELD_START_SECONDS and wave_number % 4 == 0
        pattern = formation_pattern_for_tier(tier, self._wave_count, targeted=targeted)
        kind = available_enemy_kinds_for_elapsed(elapsed_time)[
            self._wave_count % len(available_enemy_kinds_for_elapsed(elapsed_time))
        ]

        vertical_padding = SPAWN_MARGIN + max(abs(offset_y) for _, offset_y in pattern)
        if kind is EnemyKind.SWOOPER:
            vertical_padding += SWOOPER_AMPLITUDE

        if targeted:
            anchor_y = _clamp(
                player_position.y + self._rng.uniform(-TARGETED_JITTER, TARGETED_JITTER),
                minimum=vertical_padding,
                maximum=self.board_height - vertical_padding,
            )
        else:
            anchor_y = self._rng.uniform(vertical_padding, self.board_height - vertical_padding)

        enemies: list[Enemy] = []
        for offset_x, offset_y in pattern:
            base_y = anchor_y + offset_y
            phase = self._rng.uniform(0.0, math.tau) if kind is EnemyKind.SWOOPER else 0.0
            position_y = base_y
            if kind is EnemyKind.SWOOPER:
                position_y = base_y + math.sin(phase) * SWOOPER_AMPLITUDE
            enemies.append(
                Enemy(
                    kind=kind,
                    position=Vector(self.board_width + 36.0 + offset_x, position_y),
                    base_y=base_y,
                    age=0.0,
                    phase=phase,
                    fire_timer=GUNSHIP_FIRE_INITIAL_DELAY,
                    burst_shots_remaining=0,
                    burst_timer=0.0,
                )
            )

        mines = self._spawn_minefield(elapsed_time, player_position, minefield)
        self._wave_count += 1
        return enemies, mines

    def _spawn_minefield(
        self,
        elapsed_time: float,
        player_position: Vector,
        minefield: bool,
    ) -> list[Mine]:
        if not minefield:
            return []

        mines = [
            Mine(
                position=Vector(self.board_width + 68.0, player_position.y),
                ttl=MINE_TTL_SECONDS,
                pulse=self._rng.uniform(0.0, math.tau),
            )
        ]
        if elapsed_time < SECOND_MINEFIELD_SECONDS:
            return mines

        direction = -1.0 if player_position.y > self.board_height / 2.0 else 1.0
        second_y = _clamp(
            player_position.y + direction * MINE_OFFSET_DISTANCE,
            minimum=MINE_RADIUS + 12.0,
            maximum=self.board_height - MINE_RADIUS - 12.0,
        )
        mines.append(
            Mine(
                position=Vector(self.board_width + 122.0, second_y),
                ttl=MINE_TTL_SECONDS,
                pulse=self._rng.uniform(0.0, math.tau),
            )
        )
        return mines

    def _resolve_player_projectile_hits(
        self,
        player_projectiles: list[Projectile],
        enemies: list[Enemy],
        pickups: list[Pickup],
        score: int,
        kills: int,
    ) -> tuple[list[Projectile], list[Enemy], list[Pickup], int, int, list[StarfighterEvent]]:
        kept_projectiles: list[Projectile] = []
        removed_enemy_indices: set[int] = set()
        events: list[StarfighterEvent] = []

        for projectile in player_projectiles:
            hit_index = None
            for index, enemy in enumerate(enemies):
                if index in removed_enemy_indices:
                    continue
                if _circles_overlap(
                    projectile.position,
                    projectile.radius,
                    enemy.position,
                    enemy_radius_for_kind(enemy.kind),
                ):
                    hit_index = index
                    break

            if hit_index is None:
                kept_projectiles.append(projectile)
                continue

            removed_enemy_indices.add(hit_index)
            enemy = enemies[hit_index]
            score += score_for_enemy_kind(enemy.kind)
            kills += 1
            events.append(StarfighterEvent("enemy_destroyed", enemy.position))
            drop = pickup_for_kill_count(kills)
            if drop is not None:
                pickups.append(
                    Pickup(
                        kind=drop,
                        position=enemy.position,
                        base_y=enemy.position.y,
                        age=0.0,
                    )
                )

        kept_enemies = [enemy for index, enemy in enumerate(enemies) if index not in removed_enemy_indices]
        return kept_projectiles, kept_enemies, pickups, score, kills, events

    def _collect_pickups(
        self,
        pickups: list[Pickup],
        player_position: Vector,
        weapon_level: int,
        shields: int,
        score: int,
    ) -> tuple[list[Pickup], int, int, int, list[StarfighterEvent]]:
        kept_pickups: list[Pickup] = []
        events: list[StarfighterEvent] = []

        for pickup in pickups:
            if not _circles_overlap(player_position, PLAYER_RADIUS, pickup.position, 13.0):
                kept_pickups.append(pickup)
                continue

            events.append(StarfighterEvent("pickup_collected", pickup.position))
            if pickup.kind is PickupType.WEAPON:
                weapon_level = min(MAX_WEAPON_LEVEL, weapon_level + 1)
            elif pickup.kind is PickupType.SHIELD:
                if shields < MAX_SHIELDS:
                    shields += 1
                else:
                    score += FULL_SHIELD_SCORE_BONUS
            else:
                score += PICKUP_SCORE_BONUS

        return kept_pickups, weapon_level, shields, score, events

    def _resolve_player_damage(
        self,
        mines: list[Mine],
        enemies: list[Enemy],
        enemy_projectiles: list[Projectile],
        player_position: Vector,
        shields: int,
        invulnerability: float,
    ) -> tuple[list[Mine], list[Enemy], list[Projectile], int, float, list[StarfighterEvent]]:
        kept_mines: list[Mine] = []
        kept_enemies: list[Enemy] = []
        kept_projectiles: list[Projectile] = []
        events: list[StarfighterEvent] = []
        took_damage = False

        for mine in mines:
            collided = _circles_overlap(player_position, PLAYER_RADIUS, mine.position, MINE_RADIUS)
            if not collided:
                kept_mines.append(mine)
                continue
            if invulnerability <= 0.0 and not took_damage:
                shields -= 1
                invulnerability = INVULNERABILITY_DURATION
                took_damage = True
                events.append(StarfighterEvent("player_hit", player_position))

        for enemy in enemies:
            collided = _circles_overlap(
                player_position,
                PLAYER_RADIUS,
                enemy.position,
                enemy_radius_for_kind(enemy.kind),
            )
            if not collided:
                kept_enemies.append(enemy)
                continue
            if invulnerability <= 0.0 and not took_damage:
                shields -= 1
                invulnerability = INVULNERABILITY_DURATION
                took_damage = True
                events.append(StarfighterEvent("player_hit", player_position))

        for projectile in enemy_projectiles:
            collided = _circles_overlap(
                player_position,
                PLAYER_RADIUS,
                projectile.position,
                projectile.radius,
            )
            if not collided:
                kept_projectiles.append(projectile)
                continue
            if invulnerability <= 0.0 and not took_damage:
                shields -= 1
                invulnerability = INVULNERABILITY_DURATION
                took_damage = True
                events.append(StarfighterEvent("player_hit", player_position))

        return kept_mines, kept_enemies, kept_projectiles, max(shields, 0), invulnerability, events

    def _spawn_auto_fire(
        self,
        player_projectiles: list[Projectile],
        player_position: Vector,
        weapon_level: int,
        delta_seconds: float,
    ) -> tuple[list[Projectile], int]:
        cooldown = auto_fire_interval_for_weapon(weapon_level)
        self._auto_fire_timer -= delta_seconds
        while self._auto_fire_timer <= 0.0:
            for offset_y in PLAYER_SHOT_OFFSETS[weapon_level]:
                player_projectiles.append(
                    Projectile(
                        position=Vector(
                            player_position.x + PLAYER_RADIUS + 8.0,
                            player_position.y + offset_y,
                        ),
                        velocity=Vector(PLAYER_SHOT_SPEED, 0.0),
                        radius=PLAYER_SHOT_RADIUS,
                    )
                )
            self._auto_fire_timer += cooldown
        return player_projectiles, weapon_level


def auto_fire_interval_for_weapon(weapon_level: int) -> float:
    return AUTO_FIRE_INTERVALS[int(_clamp(weapon_level, minimum=1, maximum=MAX_WEAPON_LEVEL))]


def difficulty_tier_for_elapsed(elapsed_time: float) -> int:
    return int(max(0.0, elapsed_time) // SPAWN_INTERVAL_STEP_SECONDS)


def scroll_speed_for_elapsed(elapsed_time: float) -> float:
    increments = int(max(0.0, elapsed_time) // SCROLL_SPEED_STEP_SECONDS)
    return min(MAX_SCROLL_SPEED, START_SCROLL_SPEED + increments * SCROLL_SPEED_STEP)


def spawn_interval_for_elapsed(elapsed_time: float) -> float:
    reductions = int(max(0.0, elapsed_time) // SPAWN_INTERVAL_STEP_SECONDS)
    return max(MIN_SPAWN_INTERVAL, START_SPAWN_INTERVAL - reductions * SPAWN_INTERVAL_STEP)


def available_enemy_kinds_for_elapsed(elapsed_time: float) -> tuple[EnemyKind, ...]:
    if elapsed_time >= GUNSHIP_UNLOCK_SECONDS:
        return (EnemyKind.DRONE, EnemyKind.SWOOPER, EnemyKind.GUNSHIP)
    if elapsed_time >= SWOOPER_UNLOCK_SECONDS:
        return (EnemyKind.DRONE, EnemyKind.SWOOPER)
    return (EnemyKind.DRONE,)


def formation_pattern_for_tier(
    tier: int,
    wave_count: int,
    *,
    targeted: bool,
) -> tuple[tuple[float, float], ...]:
    if targeted:
        return PINCH_PATTERN
    if tier < 2:
        return FORMATION_PATTERNS[0]
    if tier < 4:
        return FORMATION_PATTERNS[wave_count % 2]
    return FORMATION_PATTERNS[wave_count % len(FORMATION_PATTERNS)]


def pickup_for_kill_count(kills: int) -> PickupType | None:
    if kills < 1 or kills % PICKUP_DROP_EVERY_KILLS != 0:
        return None
    return PICKUP_SEQUENCE[((kills // PICKUP_DROP_EVERY_KILLS) - 1) % len(PICKUP_SEQUENCE)]


def enemy_radius_for_kind(kind: EnemyKind) -> float:
    if kind is EnemyKind.GUNSHIP:
        return 22.0
    if kind is EnemyKind.SWOOPER:
        return 19.0
    return 16.0


def enemy_speed_for_kind(kind: EnemyKind) -> float:
    if kind is EnemyKind.GUNSHIP:
        return 88.0
    if kind is EnemyKind.SWOOPER:
        return 122.0
    return 104.0


def score_for_enemy_kind(kind: EnemyKind) -> int:
    if kind is EnemyKind.GUNSHIP:
        return GUNSHIP_SCORE
    if kind is EnemyKind.SWOOPER:
        return SWOOPER_SCORE
    return DRONE_SCORE


def _clamp(value: float, *, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _clamp_direction(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def _normalized_vector(vector: Vector) -> Vector:
    length = math.hypot(vector.x, vector.y)
    if length == 0.0:
        return Vector(0.0, 0.0)
    return Vector(vector.x / length, vector.y / length)


def _aimed_velocity(origin: Vector, target: Vector, speed: float) -> Vector:
    direction = _normalized_vector(Vector(target.x - origin.x, target.y - origin.y))
    return Vector(direction.x * speed, direction.y * speed)


def _circles_overlap(center_a: Vector, radius_a: float, center_b: Vector, radius_b: float) -> bool:
    return math.dist((center_a.x, center_a.y), (center_b.x, center_b.y)) <= radius_a + radius_b
