"""Кроссплатформенные пути для config и cache."""
import os
import sys
from pathlib import Path

try:
    from platformdirs import user_config_dir, user_cache_dir
    HAS_PLATFORMDIRS = True
except ImportError:
    HAS_PLATFORMDIRS = False

APP_NAME = "spb-gtfs-gpx"
APP_AUTHOR = "spb-gtfs-gpx"


def is_frozen() -> bool:
    """Проверяем, запущено ли приложение из PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_app_dir() -> Path:
    """Базовая директория приложения."""
    if is_frozen():
        # PyInstaller: _MEIPASS или директория exe
        base = Path(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
    else:
        base = Path(__file__).resolve().parent.parent
    return base


def get_config_dir() -> Path:
    """Директория для config.json."""
    if HAS_PLATFORMDIRS:
        path = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    else:
        if sys.platform == "win32":
            path = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
        elif sys.platform == "darwin":
            path = Path.home() / "Library/Application Support" / APP_NAME
        else:
            path = Path.home() / ".config" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cache_dir() -> Path:
    """Директория для кэша GTFS."""
    if HAS_PLATFORMDIRS:
        path = Path(user_cache_dir(APP_NAME, APP_AUTHOR))
    else:
        if sys.platform == "win32":
            path = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME / "cache"
        elif sys.platform == "darwin":
            path = Path.home() / "Library/Caches" / APP_NAME
        else:
            path = Path.home() / ".cache" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def get_feed_cache_dir(feed_name: str) -> Path:
    """Директория кэша для конкретного источника фида."""
    path = get_cache_dir() / "feeds" / _sanitize_filename(feed_name)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sanitize_filename(name: str) -> str:
    """Очищаем имя для использования в пути."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
