# Minigame Collection

A small desktop minigame collection built with `pygame` and managed with `uv`. The first playable game is Snake, launched from a reusable collection menu so more games can be added later without changing the app entrypoint.

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

### Snake

- `Arrows` / `WASD`: move the snake
- `Esc`: return to the menu
- `Enter`: restart after game over

## Development

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
