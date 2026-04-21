from __future__ import annotations

# ruff: noqa: E402

import os
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from minigame_collection.config import APP_CONFIG
from minigame_collection.games import build_game_registry
from minigame_collection.games.blockfall.logic import (
    BOARD_ROWS,
    BlockfallState,
    FallingPiece,
    GridPoint,
    empty_board,
)
from minigame_collection.games.blockfall.scene import BlockfallScene
from minigame_collection.games.breakout.logic import BreakoutPhase, Vector as BreakoutVector
from minigame_collection.games.breakout.scene import BreakoutScene
from minigame_collection.games.snake.logic import Direction, Point, SnakeState
from minigame_collection.games.snake.scene import SnakeScene
from minigame_collection.games.starfighter.logic import (
    Enemy,
    EnemyKind,
    Mine,
    Pickup,
    PickupType,
    Projectile,
    StarfighterPhase,
    Vector as StarfighterVector,
)
from minigame_collection.games.starfighter.scene import StarfighterScene
from minigame_collection.scene import Scene
from minigame_collection.scenes.menu import MainMenuScene
from minigame_collection.scores import ScoreEntry


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "docs" / "images"
MENU_IMAGE = IMAGE_DIR / "minigame-collection-menu.png"
GAMEPLAY_IMAGE = IMAGE_DIR / "minigame-collection-gameplay.png"

COMPOSITE_BACKGROUND = (9, 13, 25)
COMPOSITE_LABEL = (242, 247, 255)
COMPOSITE_BORDER = (87, 134, 194)
COMPOSITE_PANEL_SIZE = (520, 470)
COMPOSITE_MARGIN = 36
COMPOSITE_GAP = 30
COMPOSITE_LABEL_HEIGHT = 42
COMPOSITE_ROW_GAP = 34


class PreviewScoreStore:
    @property
    def available(self) -> bool:
        return False

    def top_scores(self, game_id: str, limit: int = 5) -> list[ScoreEntry]:
        return []

    def qualifies(self, game_id: str, score: int, limit: int = 5) -> bool:
        return False

    def save_score(self, game_id: str, player_name: str, score: int) -> bool:
        return False


def main() -> int:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    pygame.init()
    pygame.display.set_mode(APP_CONFIG.window_size)

    try:
        menu = _render_menu()
        pygame.image.save(menu, MENU_IMAGE)

        gameplay = _render_gameplay_composite()
        pygame.image.save(gameplay, GAMEPLAY_IMAGE)
    finally:
        pygame.quit()

    print(f"Wrote {MENU_IMAGE.relative_to(ROOT)}")
    print(f"Wrote {GAMEPLAY_IMAGE.relative_to(ROOT)}")
    return 0


def _render_menu() -> pygame.Surface:
    registry = build_game_registry(PreviewScoreStore())
    scene = MainMenuScene(registry.list_games())
    for _ in range(len(registry.list_games()) - 1):
        scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    scene.update(0.6)
    return _render_scene(scene)


def _render_gameplay_composite() -> pygame.Surface:
    panels = (
        ("Snake", _render_snake()),
        ("Blockfall", _render_blockfall()),
        ("Breakout", _render_breakout()),
        ("Starfighter", _render_starfighter()),
    )

    panel_width, panel_height = COMPOSITE_PANEL_SIZE
    width = COMPOSITE_MARGIN * 2 + panel_width * 2 + COMPOSITE_GAP
    height = (
        COMPOSITE_MARGIN * 2
        + (COMPOSITE_LABEL_HEIGHT + panel_height) * 2
        + COMPOSITE_ROW_GAP
    )
    composite = pygame.Surface((width, height))
    composite.fill(COMPOSITE_BACKGROUND)

    label_font = pygame.font.Font(None, 34)
    for index, (title, source) in enumerate(panels):
        column = index % 2
        row = index // 2
        left = COMPOSITE_MARGIN + column * (panel_width + COMPOSITE_GAP)
        top = COMPOSITE_MARGIN + row * (
            COMPOSITE_LABEL_HEIGHT + panel_height + COMPOSITE_ROW_GAP
        )
        _draw_composite_panel(composite, source, title, left, top, label_font)

    return composite


def _draw_composite_panel(
    target: pygame.Surface,
    source: pygame.Surface,
    title: str,
    left: int,
    top: int,
    label_font: pygame.font.Font,
) -> None:
    panel_width, panel_height = COMPOSITE_PANEL_SIZE
    label = label_font.render(title, True, COMPOSITE_LABEL)
    label_rect = label.get_rect(center=(left + panel_width // 2, top + COMPOSITE_LABEL_HEIGHT // 2))
    target.blit(label, label_rect)

    panel_rect = pygame.Rect(left, top + COMPOSITE_LABEL_HEIGHT, panel_width, panel_height)
    scaled = pygame.transform.smoothscale(source, COMPOSITE_PANEL_SIZE)
    target.blit(scaled, panel_rect)
    pygame.draw.rect(target, COMPOSITE_BORDER, panel_rect, width=2, border_radius=8)


def _render_snake() -> pygame.Surface:
    scene = SnakeScene(PreviewScoreStore())
    scene._elapsed = 0.8
    scene._game.state = SnakeState(
        body=(
            Point(15, 8),
            Point(14, 8),
            Point(13, 8),
            Point(12, 8),
            Point(12, 9),
            Point(11, 9),
            Point(10, 9),
            Point(9, 9),
            Point(9, 8),
            Point(8, 8),
            Point(7, 8),
            Point(7, 7),
            Point(6, 7),
            Point(5, 7),
        ),
        direction=Direction.RIGHT,
        pending_direction=Direction.RIGHT,
        food=Point(18, 6),
        score=12,
        alive=True,
    )
    return _render_scene(scene)


def _render_blockfall() -> pygame.Surface:
    scene = BlockfallScene(PreviewScoreStore())
    scene._elapsed = 1.0
    scene._game.state = BlockfallState(
        board=_blockfall_board(),
        active_piece=FallingPiece("T", 1, GridPoint(3, 5)),
        next_kind="I",
        score=1280,
        lines_cleared=14,
        level=1,
        alive=True,
    )
    return _render_scene(scene)


def _blockfall_board() -> tuple[tuple[str | None, ...], ...]:
    rows = [list(row) for row in empty_board()]
    stacks: dict[int, tuple[str | None, ...]] = {
        19: ("Z", "Z", None, "L", "L", "O", "O", "I", "I", None),
        18: (None, "Z", "Z", "L", None, "O", "O", "I", "T", "T"),
        17: ("J", "J", "S", "S", None, "T", "T", "T", None, "L"),
        16: ("J", None, None, "S", "S", "I", "I", "I", "I", "L"),
        15: ("J", "O", "O", None, "Z", "Z", None, "S", "S", "L"),
        14: (None, "O", "O", None, None, "Z", "Z", None, "S", "L"),
        13: (None, None, "T", "T", "T", None, "J", "J", "J", None),
        12: (None, None, None, "T", None, None, "J", None, None, None),
    }

    for row_index, row in stacks.items():
        rows[row_index] = list(row)

    return tuple(tuple(row) for row in rows[:BOARD_ROWS])[:BOARD_ROWS]


def _render_breakout() -> pygame.Surface:
    scene = BreakoutScene(PreviewScoreStore())
    scene._elapsed = 1.2
    bricks = tuple(
        brick
        for brick in scene._game.state.bricks
        if not (brick.row < 2 and brick.column in {3, 4, 5, 6})
    )
    scene._game.state = replace(
        scene._game.state,
        paddle_center_x=438.0,
        ball_position=BreakoutVector(410.0, 334.0),
        ball_velocity=BreakoutVector(220.0, -285.0),
        bricks=bricks,
        score=800,
        lives=2,
        phase=BreakoutPhase.PLAYING,
    )
    return _render_scene(scene)


def _render_starfighter() -> pygame.Surface:
    scene = StarfighterScene(PreviewScoreStore())
    scene._elapsed = 4.2
    scene._game.state = replace(
        scene._game.state,
        player_position=StarfighterVector(168.0, 286.0),
        shields=2,
        weapon_level=3,
        enemies=(
            Enemy(
                kind=EnemyKind.DRONE,
                position=StarfighterVector(452.0, 172.0),
                base_y=172.0,
                age=0.4,
                phase=0.0,
                fire_timer=0.6,
                burst_shots_remaining=0,
                burst_timer=0.0,
            ),
            Enemy(
                kind=EnemyKind.SWOOPER,
                position=StarfighterVector(560.0, 322.0),
                base_y=322.0,
                age=0.7,
                phase=0.9,
                fire_timer=0.6,
                burst_shots_remaining=0,
                burst_timer=0.0,
            ),
            Enemy(
                kind=EnemyKind.GUNSHIP,
                position=StarfighterVector(642.0, 236.0),
                base_y=236.0,
                age=0.2,
                phase=0.0,
                fire_timer=0.2,
                burst_shots_remaining=1,
                burst_timer=0.1,
            ),
        ),
        player_projectiles=(
            Projectile(
                position=StarfighterVector(272.0, 274.0),
                velocity=StarfighterVector(540.0, 0.0),
                radius=5.0,
            ),
            Projectile(
                position=StarfighterVector(330.0, 298.0),
                velocity=StarfighterVector(540.0, 0.0),
                radius=5.0,
            ),
        ),
        enemy_projectiles=(
            Projectile(
                position=StarfighterVector(374.0, 230.0),
                velocity=StarfighterVector(-330.0, 120.0),
                radius=6.0,
            ),
        ),
        pickups=(
            Pickup(
                kind=PickupType.WEAPON,
                position=StarfighterVector(420.0, 390.0),
                base_y=390.0,
                age=0.5,
            ),
        ),
        mines=(Mine(position=StarfighterVector(540.0, 438.0), ttl=3.4, pulse=0.7),),
        elapsed_time=28.0,
        distance=840,
        score=1260,
        kills=11,
        phase=StarfighterPhase.PLAYING,
    )
    return _render_scene(scene)


def _render_scene(scene: Scene) -> pygame.Surface:
    surface = pygame.Surface(APP_CONFIG.window_size)
    scene.render(surface)
    return surface


if __name__ == "__main__":
    raise SystemExit(main())
