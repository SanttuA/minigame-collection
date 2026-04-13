from __future__ import annotations

from dataclasses import dataclass


Color = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class AppConfig:
    window_width: int = 752
    window_height: int = 680
    target_fps: int = 60
    grid_columns: int = 22
    grid_rows: int = 16
    cell_size: int = 32
    hud_height: int = 120
    padding: int = 24

    @property
    def window_size(self) -> tuple[int, int]:
        return (self.window_width, self.window_height)

    @property
    def playfield_origin(self) -> tuple[int, int]:
        return (self.padding, self.hud_height + self.padding)

    @property
    def playfield_size(self) -> tuple[int, int]:
        return (
            self.grid_columns * self.cell_size,
            self.grid_rows * self.cell_size,
        )


APP_CONFIG = AppConfig()
