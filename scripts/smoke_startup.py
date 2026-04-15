from __future__ import annotations

import threading
import time

import pygame

from minigame_collection.app import run


def stop_soon() -> None:
    time.sleep(0.2)
    pygame.event.post(pygame.event.Event(pygame.QUIT))


if __name__ == "__main__":
    threading.Thread(target=stop_soon, daemon=True).start()
    raise SystemExit(run())
