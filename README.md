# Minigame Collection

A desktop minigame collection built with `pygame` and managed with `uv`. Playable games launch from a reusable collection menu so more arcade experiments can be added later without changing the app entrypoint.

## Windows Release

The first public release is `v1.0.0` and ships as a Windows portable zip.

1. Download `minigame-collection-windows-x64-v1.0.0.zip` from GitHub Releases.
2. Extract the zip to a normal folder such as `Downloads` or `Desktop`.
3. Run `Minigame Collection.exe`.

Notes:

- The Windows build is unsigned for v1, so SmartScreen may show an unknown publisher warning before launch.
- Saved scores are stored in `%LOCALAPPDATA%\Minigame Collection\scores.db`, so they survive replacing the extracted app folder with a newer version.
- macOS and Linux can still run the project from source.

## Requirements

- `uv`

## Setup

```bash
uv sync
```

This project targets Python `3.12`.

## Run From Source

Launch through the package module:

```bash
uv run python -m minigame_collection
```

Or use the console entrypoint:

```bash
uv run minigame-collection
```

## Windows Packaging

Build the Windows release on a Windows machine:

```powershell
./scripts/build_windows.ps1
```

Packaging details and the manual smoke checklist live in [packaging/windows/README.md](packaging/windows/README.md).

## Controls

### Collection Menu

- `Up` / `W`: move selection up
- `Down` / `S`: move selection down
- `Enter`: launch the selected game
- `Esc`: quit the collection

## Games

- `Snake`: grow longer, avoid collisions, and chase faster pacing.
- `Blockfall`: stack falling pieces into complete lines before the board fills up.
- `Breakout`: guide the paddle, ricochet the ball, and clear the brick wall.
- `Starfighter`: surf the scrolling lane, auto-fire through enemy waves, and last as long as you can.

### Snake

- `Arrows` / `WASD`: move the snake
- `Esc`: return to the menu
- qualifying scores prompt for a short nickname on game over
- `Enter`: save a qualifying score, or restart from the results screen
- `Esc`: skip nickname entry, or return to the menu from the results screen

### Blockfall

- `Left` / `A`: move left, or hold to keep sliding left
- `Right` / `D`: move right, or hold to keep sliding right
- `Down` / `S`: hold for a faster soft drop
- `Up` / `W`: rotate clockwise
- `Esc`: return to the menu
- qualifying scores prompt for a short nickname on game over
- `Enter`: save a qualifying score, or restart from the results screen
- `Esc`: skip nickname entry, or return to the menu from the results screen

### Breakout

- `Left` / `A`: move the paddle left
- `Right` / `D`: move the paddle right
- `Space` / `Enter`: launch the ball when waiting to serve
- `Esc`: return to the menu
- missing the ball costs one of three lives
- qualifying scores prompt for a short nickname on the results flow

### Starfighter

- `Arrows` / `WASD`: move the ship
- auto-fire is always on
- `Esc`: return to the menu
- survive incoming drones, swoopers, and gunships while the scroll speed ramps up
- pickups rotate through weapon boosts, shield repair, and score bonuses
- qualifying scores prompt for a short nickname on game over

## Development

Contributor and agent guidance lives in [AGENTS.md](AGENTS.md).

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Install Git hooks:

```bash
uv run pre-commit install
```

Run all hooks manually:

```bash
uv run pre-commit run --all-files
```

Smoke-test app startup:

```bash
uv run python scripts/smoke_startup.py
```

Release notes for the first public version live in [docs/release-notes-v1.0.0.md](docs/release-notes-v1.0.0.md).

Project licensing is covered by [LICENSE](LICENSE), and shipped dependency notices live in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Git Workflow

Use short-lived branches for changes instead of committing directly to `main`.

Suggested branch names:

- `feature/snake-polish`
- `fix/collision-bug`
- `chore/ci-cleanup`

CI runs automatically on pushes to `main`, `feature/**`, `fix/**`, and `chore/**`, plus pull requests targeting `main`.

Typical flow:

```bash
git switch -c feature/my-change
git add .
git commit -m "Add my change"
git push -u origin feature/my-change
```

Then open a pull request into `main`.
