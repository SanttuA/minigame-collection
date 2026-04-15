# Windows Release Packaging

Build the Windows release on a Windows machine. PyInstaller does not cross-compile Windows executables from Linux or macOS.

## One-command build

From PowerShell at the repo root:

```powershell
./scripts/build_windows.ps1
```

That script will:

1. sync dev dependencies
2. run `ruff`, `pytest`, and the startup smoke check
3. build the PyInstaller `onedir` bundle
4. create `dist/minigame-collection-windows-x64-v1.0.0.zip`

## Manual build steps

```powershell
uv sync --dev
uv run ruff check .
uv run pytest
uv run python scripts/smoke_startup.py
uv run pyinstaller packaging/windows/minigame_collection.spec --noconfirm --clean
Compress-Archive -Path "dist\Minigame Collection\*" -DestinationPath "dist\minigame-collection-windows-x64-v1.0.0.zip" -CompressionLevel Optimal
```

## Manual smoke checklist

- Launch `dist\Minigame Collection\Minigame Collection.exe`.
- Confirm the menu opens with readable text at the default window size.
- Launch Snake, Blockfall, Breakout, and Starfighter, then return to the menu from each one.
- Save at least one qualifying score and confirm it persists after relaunching the app.
- Confirm scores are written to `%LOCALAPPDATA%\Minigame Collection\scores.db`.
- Extract a fresh copy of the next build and verify the existing scores still appear.

## Notes

- The Windows binary is unsigned for v1, so SmartScreen may show an unknown publisher warning.
- Upload the generated zip to GitHub Releases rather than zipping the repo itself.
