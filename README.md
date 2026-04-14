# Minigame Collection

A small desktop minigame collection built with `pygame` and managed with `uv`. Playable games launch from a reusable collection menu so more arcade experiments can be added later without changing the app entrypoint.

## Requirements

- `uv`

## Setup

```bash
uv sync
```

This project targets Python `3.12`.

## Run

Launch through the package module:

```bash
uv run python -m minigame_collection
```

Or use the console entrypoint:

```bash
uv run minigame-collection
```

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

### Snake

- `Arrows` / `WASD`: move the snake
- `Esc`: return to the menu
- qualifying scores prompt for a short nickname on game over
- `Enter`: save a qualifying score, or restart from the results screen
- `Esc`: skip nickname entry, or return to the menu from the results screen

### Blockfall

- `Left` / `A`: move left
- `Right` / `D`: move right
- `Down` / `S`: soft drop
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
