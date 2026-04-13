from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pygame


@dataclass(frozen=True, slots=True)
class LaunchGame:
    game_id: str


@dataclass(frozen=True, slots=True)
class ShowMenu:
    pass


@dataclass(frozen=True, slots=True)
class QuitApp:
    pass


SceneCommand = LaunchGame | ShowMenu | QuitApp | None


class Scene(Protocol):
    def handle_event(self, event: pygame.event.Event) -> SceneCommand:
        ...

    def update(self, delta_seconds: float) -> SceneCommand:
        ...

    def render(self, surface: pygame.Surface) -> None:
        ...
