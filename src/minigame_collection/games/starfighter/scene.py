from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import pygame

from ...config import APP_CONFIG
from ...scene import SceneCommand, ShowMenu
from ...scores import LEADERBOARD_LIMIT, LeaderboardStore, ScoreEntry
from ...ui import fit_font, wrap_text
from .logic import (
    MAX_SHIELDS,
    MAX_WEAPON_LEVEL,
    PLAYER_RADIUS,
    PickupType,
    StarfighterEvent,
    StarfighterGame,
    StarfighterPhase,
    Vector,
    enemy_radius_for_kind,
)

BACKGROUND = (7, 10, 24)
BACKGROUND_GLOW = (22, 44, 88)
PLAYFIELD = (9, 16, 34)
PLAYFIELD_BORDER = (102, 202, 255)
HUD_PANEL = (15, 24, 48)
CARD_BACKGROUND = (15, 24, 46)
INPUT_BACKGROUND = (12, 21, 40)
TEXT_MAIN = (242, 247, 255)
TEXT_MUTED = (164, 186, 222)
TEXT_STRONG = (255, 232, 176)
SHIP_MAIN = (130, 225, 255)
SHIP_SHADOW = (51, 102, 140)
PLAYER_SHOT = (136, 245, 255)
ENEMY_SHOT = (255, 142, 118)
WEAPON_PICKUP = (133, 226, 255)
SHIELD_PICKUP = (136, 255, 176)
SCORE_PICKUP = (255, 211, 114)
OVERLAY = (4, 7, 17)
SUCCESS = (126, 230, 171)
ERROR = (255, 118, 118)

STARFIGHTER_GAME_ID = "starfighter"
FIXED_STEP_SECONDS = 1.0 / 120.0
NICKNAME_MAX_LENGTH = 8
ALLOWED_NICKNAME_CHARS = {" ", "-", "_"}


@dataclass(slots=True)
class Flash:
    position: Vector
    radius: float
    ttl: float
    duration: float
    color: tuple[int, int, int]


class StarfighterSceneMode(Enum):
    PLAYING = "playing"
    ENTERING_NAME = "entering_name"
    GAME_OVER_RESULTS = "game_over_results"


class StarfighterScene:
    def __init__(
        self,
        score_store: LeaderboardStore,
        *,
        game_id: str = STARFIGHTER_GAME_ID,
    ) -> None:
        width, height = APP_CONFIG.playfield_size
        self._score_store = score_store
        self._game_id = game_id
        self._game = StarfighterGame(width, height)
        self._mode = StarfighterSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._elapsed = 0.0
        self._nickname = ""
        self._leaderboard: list[ScoreEntry] = []
        self._status_message: str | None = None
        self._effects: list[Flash] = []
        self._held_left = False
        self._held_right = False
        self._held_up = False
        self._held_down = False
        self._title_font = pygame.font.Font(None, 58)
        self._hud_font = pygame.font.Font(None, 30)
        self._meta_font = pygame.font.Font(None, 24)
        self._pickup_font = pygame.font.Font(None, 24)
        self._overlay_title_font = pygame.font.Font(None, 68)
        self._overlay_font = pygame.font.Font(None, 32)
        self._leaderboard_title_font = pygame.font.Font(None, 34)
        self._leaderboard_font = pygame.font.Font(None, 30)
        self._input_font = pygame.font.Font(None, 38)
        self._status_font = pygame.font.Font(None, 28)

    @property
    def mode(self) -> StarfighterSceneMode:
        return self._mode

    @property
    def leaderboard(self) -> tuple[ScoreEntry, ...]:
        return tuple(self._leaderboard)

    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        if self._mode is StarfighterSceneMode.PLAYING:
            if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
                return None
            return self._handle_playing_event(event)

        if event.type != pygame.KEYDOWN:
            return None
        if self._mode is StarfighterSceneMode.ENTERING_NAME:
            return self._handle_name_entry_event(event)
        return self._handle_results_event(event)

    def update(self, delta_seconds: float) -> SceneCommand:
        self._elapsed += delta_seconds
        self._advance_effects(delta_seconds)

        if self._mode is not StarfighterSceneMode.PLAYING:
            return None
        if self._game.state.phase is StarfighterPhase.LOST:
            self._begin_post_game_flow()
            return None

        self._step_accumulator += delta_seconds
        while self._step_accumulator >= FIXED_STEP_SECONDS:
            self._step_accumulator -= FIXED_STEP_SECONDS
            events = self._game.step(FIXED_STEP_SECONDS)
            self._queue_effects(events)
            if self._game.state.phase is StarfighterPhase.LOST:
                self._begin_post_game_flow()
                break
        return None

    def render(self, surface: pygame.Surface) -> None:
        surface.fill(BACKGROUND)
        self._draw_backdrop(surface)
        self._draw_hud(surface)
        self._draw_playfield(surface)
        if self._mode is not StarfighterSceneMode.PLAYING:
            self._draw_outcome_overlay(surface)

    def _handle_playing_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._clear_movement()
                return ShowMenu()
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self._held_left = True
                self._sync_movement()
                return None
            if event.key in (pygame.K_RIGHT, pygame.K_d):
                self._held_right = True
                self._sync_movement()
                return None
            if event.key in (pygame.K_UP, pygame.K_w):
                self._held_up = True
                self._sync_movement()
                return None
            if event.key in (pygame.K_DOWN, pygame.K_s):
                self._held_down = True
                self._sync_movement()
            return None

        if event.key in (pygame.K_LEFT, pygame.K_a):
            self._held_left = False
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self._held_right = False
        elif event.key in (pygame.K_UP, pygame.K_w):
            self._held_up = False
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self._held_down = False
        self._sync_movement()
        return None

    def _handle_name_entry_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            self._nickname = ""
            self._show_results()
            return None
        if event.key == pygame.K_BACKSPACE:
            self._nickname = self._nickname[:-1]
            return None
        if event.key == pygame.K_RETURN:
            self._save_entered_score()
            return None
        if len(self._nickname) >= NICKNAME_MAX_LENGTH:
            return None

        candidate = event.unicode
        if len(candidate) == 1 and self._is_allowed_nickname_character(candidate):
            self._nickname += candidate
        return None

    def _handle_results_event(self, event: pygame.event.Event) -> SceneCommand:
        if event.key == pygame.K_ESCAPE:
            return ShowMenu()
        if event.key == pygame.K_RETURN:
            self._restart_game()
        return None

    def _begin_post_game_flow(self) -> None:
        self._clear_movement()
        self._refresh_leaderboard()
        self._status_message = None
        if self._should_prompt_for_name():
            self._mode = StarfighterSceneMode.ENTERING_NAME
            self._nickname = ""
            return
        self._show_results()

    def _should_prompt_for_name(self) -> bool:
        score = self._game.state.score
        if self._game.state.phase is not StarfighterPhase.LOST:
            return False
        if not self._score_store.available or score <= 0:
            return False
        return self._score_store.qualifies(self._game_id, score, limit=LEADERBOARD_LIMIT)

    def _save_entered_score(self) -> None:
        nickname = self._nickname.strip()
        if not nickname:
            return

        saved = self._score_store.save_score(self._game_id, nickname, self._game.state.score)
        self._nickname = ""
        if saved:
            self._show_results("Score saved.")
            return
        self._show_results("Scores unavailable for this run.")

    def _show_results(self, message: str | None = None) -> None:
        self._refresh_leaderboard()
        self._mode = StarfighterSceneMode.GAME_OVER_RESULTS
        if message is not None:
            self._status_message = message
            return
        if not self._score_store.available:
            self._status_message = "Scores unavailable for this run."
        else:
            self._status_message = None

    def _refresh_leaderboard(self) -> None:
        self._leaderboard = self._score_store.top_scores(
            self._game_id,
            limit=LEADERBOARD_LIMIT,
        )

    def _restart_game(self) -> None:
        self._game.reset()
        self._mode = StarfighterSceneMode.PLAYING
        self._step_accumulator = 0.0
        self._nickname = ""
        self._leaderboard = []
        self._status_message = None
        self._effects = []
        self._clear_movement()

    def _is_allowed_nickname_character(self, character: str) -> bool:
        return character.isascii() and (
            character.isalnum() or character in ALLOWED_NICKNAME_CHARS
        )

    def _sync_movement(self) -> None:
        horizontal = int(self._held_right) - int(self._held_left)
        vertical = int(self._held_down) - int(self._held_up)
        self._game.set_movement(horizontal, vertical)

    def _clear_movement(self) -> None:
        self._held_left = False
        self._held_right = False
        self._held_up = False
        self._held_down = False
        self._game.set_movement(0, 0)

    def _queue_effects(self, events: tuple[StarfighterEvent, ...]) -> None:
        for event in events:
            if event.kind == "enemy_destroyed":
                self._effects.append(
                    Flash(
                        position=event.position,
                        radius=24.0,
                        ttl=0.24,
                        duration=0.24,
                        color=(255, 182, 92),
                    )
                )
            elif event.kind == "pickup_collected":
                self._effects.append(
                    Flash(
                        position=event.position,
                        radius=18.0,
                        ttl=0.22,
                        duration=0.22,
                        color=(162, 255, 201),
                    )
                )
            elif event.kind == "player_hit":
                self._effects.append(
                    Flash(
                        position=event.position,
                        radius=34.0,
                        ttl=0.32,
                        duration=0.32,
                        color=(133, 215, 255),
                    )
                )

    def _advance_effects(self, delta_seconds: float) -> None:
        kept_effects: list[Flash] = []
        for effect in self._effects:
            ttl = effect.ttl - delta_seconds
            if ttl > 0.0:
                kept_effects.append(
                    Flash(
                        position=effect.position,
                        radius=effect.radius,
                        ttl=ttl,
                        duration=effect.duration,
                        color=effect.color,
                    )
                )
        self._effects = kept_effects

    def _draw_backdrop(self, surface: pygame.Surface) -> None:
        pulse = (math.sin(self._elapsed * 1.4) + 1.0) / 2.0
        pygame.draw.circle(
            surface,
            BACKGROUND_GLOW,
            (112, 104),
            int(82 + pulse * 16),
        )
        pygame.draw.circle(
            surface,
            (13, 28, 59),
            (APP_CONFIG.window_width - 118, 92),
            106,
        )
        pygame.draw.rect(surface, (11, 18, 38), (0, 106, APP_CONFIG.window_width, 8))

    def _draw_hud(self, surface: pygame.Surface) -> None:
        panel_rect = pygame.Rect(16, 16, APP_CONFIG.window_width - 32, 96)
        pygame.draw.rect(surface, HUD_PANEL, panel_rect, border_radius=24)
        pygame.draw.rect(surface, PLAYFIELD_BORDER, panel_rect, width=2, border_radius=24)

        title = self._title_font.render("Starfighter", True, TEXT_MAIN)
        status_text = self._status_text()
        status_font = fit_font(
            status_text,
            max_width=panel_rect.width - title.get_width() - 88,
            starting_size=30,
            min_size=18,
        )
        status = status_font.render(status_text, True, TEXT_MUTED)
        score = self._meta_font.render(f"Score {self._game.state.score:05d}", True, TEXT_MAIN)
        distance = self._meta_font.render(
            f"Distance {self._game.state.distance}",
            True,
            TEXT_MAIN,
        )
        shields = self._meta_font.render(
            f"Shields {self._game.state.shields}/{MAX_SHIELDS}",
            True,
            TEXT_STRONG,
        )
        weapon = self._meta_font.render(
            f"Weapon Lv {self._game.state.weapon_level}/{MAX_WEAPON_LEVEL}",
            True,
            TEXT_MAIN,
        )

        surface.blit(title, (34, 24))
        surface.blit(status, (title.get_width() + 54, 34))
        surface.blit(score, (36, 70))
        surface.blit(distance, (202, 70))
        surface.blit(shields, (390, 70))
        surface.blit(weapon, (560, 70))

    def _status_text(self) -> str:
        if self._game.state.invulnerability_timer > 0.0:
            return "Hull breach recovered: shields are blinking back online"
        return "Arrows / WASD to move   •   Auto-fire online   •   Esc to menu"

    def _draw_playfield(self, surface: pygame.Surface) -> None:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        width, height = APP_CONFIG.playfield_size
        playfield_rect = pygame.Rect(origin_x, origin_y, width, height)
        pygame.draw.rect(surface, PLAYFIELD, playfield_rect, border_radius=18)

        self._draw_starfield(surface, playfield_rect)
        self._draw_pickups(surface)
        self._draw_enemy_projectiles(surface)
        self._draw_player_projectiles(surface)
        self._draw_enemies(surface)
        self._draw_player(surface)
        self._draw_effects(surface, playfield_rect)

        pygame.draw.rect(surface, PLAYFIELD_BORDER, playfield_rect, width=2, border_radius=18)

    def _draw_starfield(self, surface: pygame.Surface, playfield_rect: pygame.Rect) -> None:
        width, height = playfield_rect.size
        layers = (
            (18, 48.0, 2, (68, 104, 156)),
            (14, 86.0, 3, (92, 159, 228)),
            (10, 142.0, 4, (201, 229, 255)),
        )
        for layer_index, (count, speed, radius, color) in enumerate(layers):
            for index in range(count):
                offset = ((index * 89) + layer_index * 53) % (width + 80)
                x = playfield_rect.x + width - ((self._elapsed * speed + offset) % (width + 80))
                y = playfield_rect.y + 18 + ((index * 57 + layer_index * 67) % (height - 36))
                if radius <= 2:
                    pygame.draw.line(
                        surface,
                        color,
                        (round(x), y),
                        (round(x + 5 + layer_index * 2), y),
                        1,
                    )
                else:
                    pygame.draw.circle(surface, color, (round(x), y), radius)

        band_y = playfield_rect.y + height - 94
        pygame.draw.rect(surface, (13, 24, 47), (playfield_rect.x, band_y, width, 54))
        pygame.draw.rect(surface, (15, 33, 61), (playfield_rect.x, band_y + 54, width, 40))

    def _draw_player(self, surface: pygame.Surface) -> None:
        center_x, center_y = self._screen_point(self._game.state.player_position)
        engine_pulse = 4 + math.sin(self._elapsed * 12.0) * 2.0
        flame = [
            (center_x - 20, center_y),
            (center_x - 34 - engine_pulse, center_y - 7),
            (center_x - 28 - engine_pulse, center_y),
            (center_x - 34 - engine_pulse, center_y + 7),
        ]
        pygame.draw.polygon(surface, (255, 169, 84), flame)

        shadow_points = [
            (center_x + 18, center_y),
            (center_x - 8, center_y - 16),
            (center_x - 19, center_y - 8),
            (center_x - 15, center_y),
            (center_x - 19, center_y + 8),
            (center_x - 8, center_y + 16),
        ]
        body_points = [
            (center_x + 16, center_y),
            (center_x - 6, center_y - 14),
            (center_x - 17, center_y - 7),
            (center_x - 12, center_y),
            (center_x - 17, center_y + 7),
            (center_x - 6, center_y + 14),
        ]
        pygame.draw.polygon(surface, SHIP_SHADOW, shadow_points)
        pygame.draw.polygon(surface, SHIP_MAIN, body_points)
        pygame.draw.polygon(
            surface,
            (255, 252, 214),
            [(center_x + 9, center_y), (center_x - 2, center_y - 5), (center_x - 2, center_y + 5)],
        )
        pygame.draw.line(
            surface,
            (255, 255, 255),
            (center_x - 4, center_y - 10),
            (center_x + 7, center_y),
            2,
        )
        pygame.draw.line(
            surface,
            (255, 255, 255),
            (center_x - 4, center_y + 10),
            (center_x + 7, center_y),
            2,
        )

        if self._game.state.invulnerability_timer > 0.0 and int(self._elapsed * 14.0) % 2 == 0:
            pygame.draw.circle(
                surface,
                (184, 236, 255),
                (center_x, center_y),
                int(PLAYER_RADIUS + 8),
                2,
            )

    def _draw_enemies(self, surface: pygame.Surface) -> None:
        for enemy in self._game.state.enemies:
            center_x, center_y = self._screen_point(enemy.position)
            radius = int(enemy_radius_for_kind(enemy.kind))
            if enemy.kind.value == "drone":
                points = [
                    (center_x - radius, center_y),
                    (center_x, center_y - radius + 2),
                    (center_x + radius, center_y),
                    (center_x, center_y + radius - 2),
                ]
                pygame.draw.polygon(surface, (180, 91, 100), points)
                pygame.draw.polygon(
                    surface,
                    (255, 127, 120),
                    [(center_x - radius + 4, center_y), (center_x, center_y - 8), (center_x + radius - 4, center_y), (center_x, center_y + 8)],
                )
            elif enemy.kind.value == "swooper":
                wing = radius + 6
                points = [
                    (center_x + radius, center_y),
                    (center_x - 2, center_y - 10),
                    (center_x - wing, center_y - 2),
                    (center_x - 6, center_y),
                    (center_x - wing, center_y + 2),
                    (center_x - 2, center_y + 10),
                ]
                pygame.draw.polygon(surface, (90, 135, 255), points)
                pygame.draw.polygon(
                    surface,
                    (162, 193, 255),
                    [(center_x + radius - 4, center_y), (center_x - 2, center_y - 6), (center_x - 10, center_y), (center_x - 2, center_y + 6)],
                )
            else:
                body = pygame.Rect(center_x - radius, center_y - 14, radius * 2, 28)
                pygame.draw.rect(surface, (110, 166, 92), body, border_radius=10)
                pygame.draw.rect(surface, (177, 233, 142), body.inflate(-8, -8), border_radius=8)
                turret = pygame.Rect(center_x + 6, center_y - 4, 16, 8)
                pygame.draw.rect(surface, (236, 246, 194), turret, border_radius=4)

    def _draw_player_projectiles(self, surface: pygame.Surface) -> None:
        for projectile in self._game.state.player_projectiles:
            center_x, center_y = self._screen_point(projectile.position)
            pygame.draw.line(
                surface,
                PLAYER_SHOT,
                (center_x - 8, center_y),
                (center_x + 7, center_y),
                3,
            )

    def _draw_enemy_projectiles(self, surface: pygame.Surface) -> None:
        for projectile in self._game.state.enemy_projectiles:
            center_x, center_y = self._screen_point(projectile.position)
            pygame.draw.circle(surface, ENEMY_SHOT, (center_x, center_y), int(projectile.radius))
            pygame.draw.circle(surface, (255, 229, 182), (center_x - 1, center_y - 1), 2)

    def _draw_pickups(self, surface: pygame.Surface) -> None:
        for pickup in self._game.state.pickups:
            center_x, center_y = self._screen_point(pickup.position)
            color, label = self._pickup_style(pickup.kind)
            pygame.draw.circle(surface, color, (center_x, center_y), 13)
            pygame.draw.circle(surface, (255, 255, 255), (center_x, center_y), 13, 2)
            text = self._pickup_font.render(label, True, PLAYFIELD)
            surface.blit(text, text.get_rect(center=(center_x, center_y + 1)))

    def _pickup_style(self, pickup_type: PickupType) -> tuple[tuple[int, int, int], str]:
        if pickup_type is PickupType.WEAPON:
            return WEAPON_PICKUP, "W"
        if pickup_type is PickupType.SHIELD:
            return SHIELD_PICKUP, "S"
        return SCORE_PICKUP, "$"

    def _draw_effects(self, surface: pygame.Surface, playfield_rect: pygame.Rect) -> None:
        overlay = pygame.Surface(APP_CONFIG.playfield_size, pygame.SRCALPHA)
        for effect in self._effects:
            progress = effect.ttl / effect.duration
            radius = round(effect.radius * (1.0 + (1.0 - progress) * 0.4))
            alpha = round(190 * progress)
            center_x = round(effect.position.x)
            center_y = round(effect.position.y)
            pygame.draw.circle(overlay, (*effect.color, alpha), (center_x, center_y), radius, width=3)
        surface.blit(overlay, playfield_rect.topleft)

    def _draw_outcome_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(APP_CONFIG.window_size, pygame.SRCALPHA)
        overlay.fill((*OVERLAY, 192))
        surface.blit(overlay, (0, 0))

        card_rect = pygame.Rect(88, 120, 576, 448)
        pygame.draw.rect(surface, CARD_BACKGROUND, card_rect, border_radius=28)
        pygame.draw.rect(surface, TEXT_STRONG, card_rect, width=2, border_radius=28)

        title = self._overlay_title_font.render("Systems Down", True, TEXT_MAIN)
        score = self._overlay_font.render(f"Final score: {self._game.state.score}", True, TEXT_MAIN)
        distance = self._overlay_font.render(
            f"Distance flown: {self._game.state.distance}",
            True,
            TEXT_MUTED,
        )
        surface.blit(title, title.get_rect(center=(card_rect.centerx, card_rect.y + 52)))
        surface.blit(score, score.get_rect(center=(card_rect.centerx, card_rect.y + 104)))
        surface.blit(distance, distance.get_rect(center=(card_rect.centerx, card_rect.y + 136)))

        if self._mode is StarfighterSceneMode.ENTERING_NAME:
            self._draw_name_entry(surface, card_rect)
        else:
            self._draw_results(surface, card_rect)

    def _draw_name_entry(self, surface: pygame.Surface, card_rect: pygame.Rect) -> None:
        prompt_text = "New high score! Enter a callsign"
        prompt_font = fit_font(
            prompt_text,
            max_width=card_rect.width - 56,
            starting_size=32,
            min_size=24,
        )
        prompt = prompt_font.render(prompt_text, True, TEXT_STRONG)
        surface.blit(prompt, prompt.get_rect(center=(card_rect.centerx, card_rect.y + 186)))

        input_rect = pygame.Rect(card_rect.x + 96, card_rect.y + 226, card_rect.width - 192, 62)
        pygame.draw.rect(surface, INPUT_BACKGROUND, input_rect, border_radius=16)
        pygame.draw.rect(surface, PLAYFIELD_BORDER, input_rect, width=2, border_radius=16)

        nickname = self._nickname or "Type up to 8 chars"
        nickname_color = TEXT_MAIN if self._nickname else TEXT_MUTED
        nickname_surface = self._input_font.render(nickname, True, nickname_color)
        surface.blit(nickname_surface, (input_rect.x + 16, input_rect.y + 11))

        if self._nickname and int(self._elapsed * 2.4) % 2 == 0:
            cursor_x = input_rect.x + 18 + nickname_surface.get_width()
            pygame.draw.line(
                surface,
                TEXT_STRONG,
                (cursor_x, input_rect.y + 12),
                (cursor_x, input_rect.bottom - 12),
                2,
            )

        details_text = "Letters, numbers, space, - and _"
        details = self._status_font.render(details_text, True, TEXT_MUTED)
        surface.blit(details, details.get_rect(center=(card_rect.centerx, card_rect.y + 324)))

        hint_text = "Enter to save   •   Esc to skip"
        hint = self._status_font.render(hint_text, True, TEXT_MUTED)
        surface.blit(hint, hint.get_rect(center=(card_rect.centerx, card_rect.y + 372)))

    def _draw_results(self, surface: pygame.Surface, card_rect: pygame.Rect) -> None:
        prompt_text = "Press Enter to launch another run or Esc to return to menu"
        prompt_font = fit_font(
            prompt_text,
            max_width=card_rect.width - 64,
            starting_size=28,
            min_size=20,
        )
        prompt_lines = wrap_text(prompt_text, prompt_font, card_rect.width - 64)
        prompt_top = card_rect.y + 176
        line_height = prompt_font.get_linesize()
        for index, line in enumerate(prompt_lines):
            prompt = prompt_font.render(line, True, TEXT_MUTED)
            surface.blit(
                prompt,
                prompt.get_rect(center=(card_rect.centerx, prompt_top + index * line_height)),
            )

        leaderboard_top = card_rect.y + 252
        if self._status_message is not None:
            status = self._status_font.render(
                self._status_message,
                True,
                self._status_color(self._status_message),
            )
            surface.blit(status, status.get_rect(center=(card_rect.centerx, card_rect.y + 228)))
            leaderboard_top += 16

        self._draw_leaderboard(surface, card_rect, top=leaderboard_top)

    def _draw_leaderboard(
        self,
        surface: pygame.Surface,
        card_rect: pygame.Rect,
        *,
        top: int,
    ) -> None:
        title = self._leaderboard_title_font.render("Top 5 Scores", True, TEXT_MAIN)
        surface.blit(title, title.get_rect(center=(card_rect.centerx, top)))

        if not self._leaderboard:
            empty = self._leaderboard_font.render("No saved scores yet.", True, TEXT_MUTED)
            surface.blit(empty, empty.get_rect(center=(card_rect.centerx, top + 46)))
            return

        start_y = top + 38
        line_height = 32
        rank_x = card_rect.x + 70
        name_x = card_rect.x + 130
        score_x = card_rect.right - 70
        for index, entry in enumerate(self._leaderboard, start=1):
            y = start_y + (index - 1) * line_height
            rank = self._leaderboard_font.render(f"{index:02d}", True, TEXT_STRONG)
            name = self._leaderboard_font.render(entry.player_name, True, TEXT_MAIN)
            score = self._leaderboard_font.render(str(entry.score), True, TEXT_MAIN)
            surface.blit(rank, (rank_x, y))
            surface.blit(name, (name_x, y))
            surface.blit(score, score.get_rect(topright=(score_x, y)))

    def _status_color(self, message: str) -> tuple[int, int, int]:
        if "unavailable" in message.lower():
            return ERROR
        return SUCCESS

    def _screen_point(self, point: Vector) -> tuple[int, int]:
        origin_x, origin_y = APP_CONFIG.playfield_origin
        return (round(origin_x + point.x), round(origin_y + point.y))


def create_starfighter_scene(score_store: LeaderboardStore) -> StarfighterScene:
    return StarfighterScene(score_store)
