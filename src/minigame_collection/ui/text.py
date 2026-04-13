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


def fit_font_to_lines(
    lines: list[str] | tuple[str, ...],
    *,
    max_width: int,
    max_height: int,
    starting_size: int,
    min_size: int,
) -> pygame.font.Font:
    for size in range(starting_size, min_size - 1, -1):
        font = pygame.font.Font(None, size)
        if _lines_fit(font, lines, max_width=max_width, max_height=max_height):
            return font
    return pygame.font.Font(None, min_size)


def fit_wrapped_text(
    text: str,
    *,
    max_width: int,
    max_height: int,
    starting_size: int,
    min_size: int,
) -> tuple[pygame.font.Font, list[str]]:
    for size in range(starting_size, min_size - 1, -1):
        font = pygame.font.Font(None, size)
        lines = wrap_text(text, font, max_width)
        if _lines_fit(font, lines, max_width=max_width, max_height=max_height):
            return font, lines

    font = pygame.font.Font(None, min_size)
    return font, wrap_text(text, font, max_width)


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


def _lines_fit(
    font: pygame.font.Font,
    lines: list[str] | tuple[str, ...],
    *,
    max_width: int,
    max_height: int,
) -> bool:
    widest_line = max((font.size(line)[0] for line in lines), default=0)
    return widest_line <= max_width and font.get_linesize() * len(lines) <= max_height
