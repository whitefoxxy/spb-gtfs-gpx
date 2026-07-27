# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Путь к проекту
base_path = Path(SPECDIR).resolve()

# Дополнительные файлы (если нужны иконки и т.п.)
added_files = []

# Найти путь к customtkinter для --add-data
import customtkinter
ctk_path = Path(customtkinter.__file__).parent
added_files.append((str(ctk_path), "customtkinter"))

a = Analysis(
    [str(base_path / "main.py")],
    pathex=[str(base_path)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "pandas",
        "pandas._libs.tslibs",
        "pandas._libs.tslibs.base",
        "gpxpy",
        "shapely",
        "shapely.geometry",
        "requests",
        "platformdirs",
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="spb-gtfs-gpx",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# Для macOS: создаём .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        name="spb-gtfs-gpx.app",
        icon=None,
        bundle_identifier="com.spbgtfsgpx.app",
    )
