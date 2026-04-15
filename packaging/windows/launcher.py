from __future__ import annotations

# PyInstaller launches this as a top-level script, so it must use an absolute
# import instead of packaging `minigame_collection.__main__` directly.
from minigame_collection.app import run


if __name__ == "__main__":
    raise SystemExit(run())
