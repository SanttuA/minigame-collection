from __future__ import annotations

import pygame

from .config import APP_CONFIG
from .games import build_game_registry
from .metadata import APP_NAME
from .registry import GameRegistry
from .scene import LaunchGame, QuitApp, Scene, SceneCommand, ShowMenu
from .scenes.menu import MainMenuScene
from .scores import SQLiteScoreStore, resolve_scores_database_path


class GameApp:
    def __init__(self) -> None:
        self._score_store = SQLiteScoreStore(resolve_scores_database_path())
        self._registry: GameRegistry = build_game_registry(self._score_store)
        self._scene: Scene | None = None

    def _create_menu_scene(self) -> MainMenuScene:
        return MainMenuScene(self._registry.list_games())

    def _apply_command(self, command: SceneCommand) -> bool:
        if command is None:
            return True
        if isinstance(command, QuitApp):
            return False
        if isinstance(command, ShowMenu):
            self._scene = self._create_menu_scene()
            return True
        if isinstance(command, LaunchGame):
            self._scene = self._registry.get(command.game_id).create_scene()
            return True
        raise ValueError(f"Unsupported scene command: {command!r}")

    def run(self) -> int:
        pygame.init()
        pygame.display.set_caption(APP_NAME)

        screen = pygame.display.set_mode(APP_CONFIG.window_size)
        clock = pygame.time.Clock()
        self._scene = self._create_menu_scene()
        running = True

        try:
            while running:
                delta_seconds = clock.tick(APP_CONFIG.target_fps) / 1000.0

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break

                    running = self._apply_command(self._scene.handle_event(event))
                    if not running:
                        break

                if not running:
                    break

                running = self._apply_command(self._scene.update(delta_seconds))
                if not running:
                    break

                self._scene.render(screen)
                pygame.display.flip()
        finally:
            pygame.quit()

        return 0


def run() -> int:
    return GameApp().run()
