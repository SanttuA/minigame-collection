$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

param(
    [switch]$SkipChecks
)

$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot

try {
    uv sync --dev

    if (-not $SkipChecks) {
        uv run ruff check .
        uv run pytest
        uv run python scripts/smoke_startup.py
    }

    if (Test-Path build) {
        Remove-Item build -Recurse -Force
    }

    if (Test-Path dist) {
        Remove-Item dist -Recurse -Force
    }

    uv run pyinstaller packaging/windows/minigame_collection.spec --noconfirm --clean

    $distDirName = uv run python -c "from minigame_collection.metadata import WINDOWS_DIST_DIR_NAME; print(WINDOWS_DIST_DIR_NAME)"
    $archiveName = uv run python -c "from minigame_collection.metadata import WINDOWS_RELEASE_ARCHIVE_NAME; print(WINDOWS_RELEASE_ARCHIVE_NAME)"
    $bundlePath = Join-Path $projectRoot "dist\$distDirName"
    $archivePath = Join-Path $projectRoot "dist\$archiveName"

    if (Test-Path $archivePath) {
        Remove-Item $archivePath -Force
    }

    Compress-Archive -Path "$bundlePath\*" -DestinationPath $archivePath -CompressionLevel Optimal
    Write-Host "Created $archivePath"
}
finally {
    Pop-Location
}
