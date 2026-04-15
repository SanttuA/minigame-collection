# Minigame Collection v1.0.0

First public release of the desktop minigame collection.

## Included games

- Snake
- Blockfall
- Breakout
- Starfighter

## Highlights

- reusable launcher flow for multiple arcade-style games
- local high-score saving across the current game set
- Windows portable build for unzip-and-run play
- automated linting, tests, and startup smoke checks in the project workflow

## Windows notes

- Download `minigame-collection-windows-x64-v1.0.0.zip`, extract it, and run `Minigame Collection.exe`.
- Saved scores live in `%LOCALAPPDATA%\Minigame Collection\scores.db`.
- The v1 Windows build is unsigned, so Windows may show an unknown publisher warning before launch.

## Known limitations

- The packaged desktop build is Windows-only for v1.
- macOS and Linux are still source-run platforms for now.
