from __future__ import annotations

import struct
import zlib
from pathlib import Path


CANVAS_SIZE = 256
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "windows"
PNG_PATH = OUTPUT_DIR / "minigame_collection.png"
ICO_PATH = OUTPUT_DIR / "minigame_collection.ico"

TRANSPARENT = (0, 0, 0, 0)
BACKGROUND = (10, 28, 38, 255)
BORDER = (120, 225, 219, 255)
SHADOW = (4, 14, 20, 180)
CENTER = (236, 245, 240, 255)
TILE_COLORS = {
    "snake": (90, 204, 112, 255),
    "blockfall": (249, 167, 48, 255),
    "breakout": (241, 94, 89, 255),
    "starfighter": (83, 163, 255, 255),
}


def build_pixels() -> list[list[tuple[int, int, int, int]]]:
    pixels = [[TRANSPARENT for _ in range(CANVAS_SIZE)] for _ in range(CANVAS_SIZE)]

    def fill_rect(left: int, top: int, right: int, bottom: int, color: tuple[int, int, int, int]) -> None:
        for y in range(top, bottom):
            for x in range(left, right):
                pixels[y][x] = color

    fill_rect(28, 36, 228, 236, SHADOW)
    fill_rect(24, 24, 224, 224, BORDER)
    fill_rect(34, 34, 214, 214, BACKGROUND)

    tile_size = 68
    gap = 12
    left = 53
    top = 53
    fill_rect(left, top, left + tile_size, top + tile_size, TILE_COLORS["snake"])
    fill_rect(
        left + tile_size + gap,
        top,
        left + 2 * tile_size + gap,
        top + tile_size,
        TILE_COLORS["blockfall"],
    )
    fill_rect(
        left,
        top + tile_size + gap,
        left + tile_size,
        top + 2 * tile_size + gap,
        TILE_COLORS["breakout"],
    )
    fill_rect(
        left + tile_size + gap,
        top + tile_size + gap,
        left + 2 * tile_size + gap,
        top + 2 * tile_size + gap,
        TILE_COLORS["starfighter"],
    )

    fill_rect(110, 110, 146, 146, CENTER)

    for offset in range(0, 150):
        start = 36 + offset
        end = max(start - 28, 34)
        y = 38 + offset
        if y >= 214:
            break
        for x in range(end, min(start, 214)):
            red, green, blue, alpha = pixels[y][x]
            if alpha == 0:
                continue
            pixels[y][x] = (
                min(red + 18, 255),
                min(green + 18, 255),
                min(blue + 18, 255),
                alpha,
            )

    return pixels


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)
    )


def encode_png(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    rows = [b"\x00" + b"".join(bytes(pixel) for pixel in row) for row in pixels]
    raw = b"".join(rows)
    ihdr = struct.pack(">IIBBBBB", CANVAS_SIZE, CANVAS_SIZE, 8, 6, 0, 0, 0)
    return b"".join(
        [
            b"\x89PNG\r\n\x1a\n",
            png_chunk(b"IHDR", ihdr),
            png_chunk(b"IDAT", zlib.compress(raw, level=9)),
            png_chunk(b"IEND", b""),
        ]
    )


def encode_ico(png_bytes: bytes) -> bytes:
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack(
        "<BBBBHHII",
        0,
        0,
        0,
        0,
        1,
        32,
        len(png_bytes),
        6 + 16,
    )
    return header + entry + png_bytes


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pixels = build_pixels()
    png_bytes = encode_png(pixels)
    PNG_PATH.write_bytes(png_bytes)
    ICO_PATH.write_bytes(encode_ico(png_bytes))


if __name__ == "__main__":
    main()
