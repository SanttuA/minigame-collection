from __future__ import annotations

import pygame
import pytest

from minigame_collection.ui import fit_font_to_lines, fit_wrapped_text


@pytest.fixture(autouse=True)
def init_pygame_font() -> None:
    pygame.font.init()
    yield
    pygame.font.quit()


def test_fit_font_to_lines_respects_width_and_height() -> None:
    lines = [
        "Left / A  Move left",
        "Right / D  Move right",
        "Down / S  Soft drop",
        "Up / W  Rotate",
        "Esc  Return to menu",
    ]

    font = fit_font_to_lines(
        lines,
        max_width=220,
        max_height=110,
        starting_size=28,
        min_size=16,
    )

    assert max(font.size(line)[0] for line in lines) <= 220
    assert font.get_linesize() * len(lines) <= 110


def test_fit_wrapped_text_respects_width_and_height() -> None:
    font, lines = fit_wrapped_text(
        "Stack clean lines before the well runs out of room.",
        max_width=200,
        max_height=60,
        starting_size=28,
        min_size=16,
    )

    assert lines
    assert max(font.size(line)[0] for line in lines) <= 200
    assert font.get_linesize() * len(lines) <= 60
