from __future__ import annotations

import pygame


def fit_font(
    text: str,
    *,
    max_width: int,
    starting_size: int,
    min_size: int,
) -> pygame.font.Font:
    for size in range(starting_size, min_size - 1, -1):
        font = pygame.font.Font(None, size)
        if font.size(text)[0] <= max_width:
            return font
    return pygame.font.Font(None, min_size)


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current_line = words[0]

    for word in words[1:]:
        candidate = f"{current_line} {word}"
        if font.size(candidate)[0] <= max_width:
            current_line = candidate
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)
    return lines
