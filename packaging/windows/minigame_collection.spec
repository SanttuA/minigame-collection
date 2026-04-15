# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import runpy

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


try:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
except NameError:
    PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
BUILD_ROOT = PROJECT_ROOT / "build" / "pyinstaller"
ICON_PATH = PROJECT_ROOT / "assets" / "windows" / "minigame_collection.ico"

metadata = runpy.run_path(str(SRC_ROOT / "minigame_collection" / "metadata.py"))
APP_NAME = metadata["APP_NAME"]
APP_VERSION = metadata["APP_VERSION"]
APP_AUTHOR = metadata["APP_AUTHOR"]
WINDOWS_EXECUTABLE_NAME = metadata["WINDOWS_EXECUTABLE_NAME"]
WINDOWS_DIST_DIR_NAME = metadata["WINDOWS_DIST_DIR_NAME"]
RELEASE_NOTICES = [
    (str(PROJECT_ROOT / "LICENSE"), "."),
    (str(PROJECT_ROOT / "THIRD_PARTY_NOTICES.md"), "."),
]

version_parts = [int(part) for part in APP_VERSION.split(".")]
version_tuple = tuple(version_parts + [0] * (4 - len(version_parts)))

version_file = BUILD_ROOT / "windows_version_info.txt"
version_file.parent.mkdir(parents=True, exist_ok=True)
version_file.write_text(
    f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          '040904B0',
          [
            StringStruct('CompanyName', '{APP_AUTHOR}'),
            StringStruct('FileDescription', 'Desktop arcade collection built with pygame'),
            StringStruct('FileVersion', '{APP_VERSION}'),
            StringStruct('InternalName', '{APP_NAME}'),
            StringStruct('OriginalFilename', '{WINDOWS_EXECUTABLE_NAME}'),
            StringStruct('ProductName', '{APP_NAME}'),
            StringStruct('ProductVersion', '{APP_VERSION}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)""",
    encoding="utf-8",
)

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "windows" / "launcher.py")],
    pathex=[str(SRC_ROOT)],
    binaries=collect_dynamic_libs("pygame"),
    datas=collect_data_files("pygame") + RELEASE_NOTICES,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=WINDOWS_EXECUTABLE_NAME.removesuffix(".exe"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ICON_PATH),
    version=str(version_file),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=WINDOWS_DIST_DIR_NAME,
)
