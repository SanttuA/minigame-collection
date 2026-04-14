# AGENTS.md

## Purpose

This repository is a small desktop minigame collection built with `pygame` and managed with `uv`.
The current v1 scope is:

- a reusable collection launcher
- registered games: Snake and Blockfall
- tests for core game logic
- local and CI checks through `pre-commit`, `ruff`, and `pytest`

Agents should preserve the collection architecture instead of turning the project into a one-off single game.

## Tooling

- Python: `3.12` from `.python-version`
- Package manager and runner: `uv`
- Runtime dependency: `pygame`
- Dev tools: `pytest`, `ruff`, `pre-commit`

Common commands:

```bash
uv sync --dev
uv run minigame-collection
uv run python -m minigame_collection
uv run ruff check .
uv run pytest
uv run pre-commit run --all-files
```

## Repository Shape

- `src/minigame_collection/app.py`: app bootstrap, main loop, scene switching
- `src/minigame_collection/registry.py`: game registration model
- `src/minigame_collection/scenes/menu.py`: launcher menu scene
- `src/minigame_collection/games/`: game implementations
- `src/minigame_collection/games/snake/logic.py`: pure Snake rules
- `src/minigame_collection/games/snake/scene.py`: `pygame` rendering and input for Snake
- `tests/`: unit and smoke-style tests

## Implementation Rules

- Keep pure game rules separate from `pygame` UI code when practical.
- Prefer extending the registry and scene system over special-casing logic in `app.py`.
- New minigames should register through `build_game_registry()` and return their own scene.
- Keep the windowed desktop flow intact: launcher -> game -> restart/menu.
- Use code-drawn visuals unless the task explicitly introduces assets.
- Favor small, composable modules over large monolithic files.

## UI Layout Guard Rails

- Do not place text with fixed font sizes into constrained panels unless width and height have both been checked.
- For new UI text, prefer the helpers in `src/minigame_collection/ui/text.py` so labels are fitted or wrapped to their bounding area before rendering.
- Treat vertical fit as a first-class constraint: line height × line count must fit the allotted space, not just the width of each line.
- When adding a new HUD, overlay, or menu card, leave explicit bottom padding so status text, controls, and footer text cannot collide.
- If scene layout changes, run a smoke check and visually sanity-check that no text clips, overlaps, or renders outside its panel at the default window size.

## Testing Expectations

Before finishing changes, run:

```bash
uv run ruff check .
uv run pytest
```

If startup or scene wiring changes, also run a smoke check. In CI this is covered by the GitHub Actions workflow in `.github/workflows/ci.yml`.

## Git Workflow

- Work on short-lived branches, not directly on `main`.
- Preferred branch prefixes:
  - `feature/`
  - `fix/`
  - `chore/`
- Keep commits focused and descriptive.
- Do not commit `.venv`, caches, or local-only tool files.

## Notes For Agents

- `.codex` is ignored and treated as local-only unless the team explicitly decides to use it as shared repo config.
- Keep `uv.lock` tracked and update it when dependencies change.
- If a newer Python version is considered, verify `pygame` compatibility before changing `requires-python`.
