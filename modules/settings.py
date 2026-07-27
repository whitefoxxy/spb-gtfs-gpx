"""Настройки приложения и модель источников фидов."""
import json
import copy
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from pathlib import Path

from .paths import get_config_path


@dataclass
class FeedSource:
    """Источник GTFS-фида."""
    name: str
    url: str
    enabled: bool = True

    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url, "enabled": self.enabled}

    @classmethod
    def from_dict(cls, d: dict) -> "FeedSource":
        return cls(name=d.get("name", ""), url=d.get("url", ""), enabled=d.get("enabled", True))


DEFAULT_FEEDS = [
    FeedSource(
        name="Санкт-Петербург",
        url="https://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs/feed.zip",
        enabled=True,
    ),
]


@dataclass
class Settings:
    """Все настройки приложения."""

    # --- Источники фидов ---
    feeds: List[FeedSource] = field(default_factory=lambda: copy.deepcopy(DEFAULT_FEEDS))

    # --- Фильтры транспорта ---
    transport_types: List[str] = field(default_factory=lambda: ["bus"])  # bus, trolley, tram
    route_numbers: str = ""  # "3,7,10-15" или пусто = все
    directions: List[int] = field(default_factory=lambda: [0, 1])  # 0=прямое, 1=обратное
    shape_mode: str = "main"  # main | all | longest
    only_active: bool = True
    active_date: str = ""  # YYYY-MM-DD, пусто = сегодня

    # --- Доп. фильтры ---
    urban_mode: str = "all"  # all | urban | suburban
    include_night: bool = True
    include_circular: bool = True

    # --- Остановки ---
    include_stops: bool = False
    stops_source: str = "selected"  # all | selected
    stop_name_field: str = "stop_name"  # stop_name | stop_code | stop_id

    # --- GPX ---
    output_single: bool = True
    output_per_route: bool = False
    merge_routes: bool = False  # объединить выбранные маршруты в один трек
    output_dir: str = ""
    track_name_template: str = "{short_name} {headsign}"
    simplify: bool = False
    simplify_tolerance_m: float = 20.0
    include_metadata: bool = True

    # --- Сеть ---
    timeout_s: int = 120
    proxy: str = ""
    user_agent: str = "spb-gtfs-gpx/1.0"
    cache_ttl_hours: int = 24

    def to_dict(self) -> dict:
        d = asdict(self)
        d["feeds"] = [f.to_dict() for f in self.feeds]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        feeds = [FeedSource.from_dict(fd) for fd in d.get("feeds", [])]
        if not feeds:
            feeds = copy.deepcopy(DEFAULT_FEEDS)
        return cls(
            feeds=feeds,
            transport_types=d.get("transport_types", ["bus"]),
            route_numbers=d.get("route_numbers", ""),
            directions=d.get("directions", [0, 1]),
            shape_mode=d.get("shape_mode", "main"),
            only_active=d.get("only_active", True),
            active_date=d.get("active_date", ""),
            urban_mode=d.get("urban_mode", "all"),
            include_night=d.get("include_night", True),
            include_circular=d.get("include_circular", True),
            include_stops=d.get("include_stops", False),
            stops_source=d.get("stops_source", "selected"),
            stop_name_field=d.get("stop_name_field", "stop_name"),
            output_single=d.get("output_single", True),
            output_per_route=d.get("output_per_route", False),
            merge_routes=d.get("merge_routes", False),
            output_dir=d.get("output_dir", ""),
            track_name_template=d.get("track_name_template", "{short_name} {headsign}"),
            simplify=d.get("simplify", False),
            simplify_tolerance_m=d.get("simplify_tolerance_m", 20.0),
            include_metadata=d.get("include_metadata", True),
            timeout_s=d.get("timeout_s", 120),
            proxy=d.get("proxy", ""),
            user_agent=d.get("user_agent", "spb-gtfs-gpx/1.0"),
            cache_ttl_hours=d.get("cache_ttl_hours", 24),
        )

    def save(self) -> None:
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls) -> "Settings":
        path = get_config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return cls.from_dict(json.load(f))
            except Exception:
                pass
        return cls()
