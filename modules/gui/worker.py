"""Фоновый поток для загрузки, парсинга и экспорта GTFS → GPX."""
import queue
import threading
import traceback
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pandas as pd

from ..gtfs_downloader import GTFSDownloader
from ..gtfs_parser import GTFSParser
from ..actuality_checker import ActualityChecker
from ..gpx_builder import GPXBuilder
from ..settings import Settings


class WorkerMessage:
    """Сообщение от worker в GUI."""
    TYPE_PROGRESS = "progress"
    TYPE_LOG = "log"
    TYPE_DONE = "done"
    TYPE_ERROR = "error"
    TYPE_ROUTES_LOADED = "routes_loaded"

    def __init__(self, msg_type: str, data: dict = None):
        self.type = msg_type
        self.data = data or {}


class GTFSWorker(threading.Thread):
    """Фоновый поток для всех операций."""

    def __init__(
        self,
        settings: Settings,
        message_queue: queue.Queue,
        mode: str = "load",  # "load" | "export"
        selected_route_ids: Optional[List[str]] = None,
        force: bool = False,
    ):
        super().__init__(daemon=True)
        self.settings = settings
        self.msg_queue = message_queue
        self.mode = mode
        self.selected_route_ids = selected_route_ids or []
        self._force = force
        self._cancelled = False
        self._parser: Optional[GTFSParser] = None
        self._routes_df: Optional[pd.DataFrame] = None

    def cancel(self):
        self._cancelled = True

    def _post(self, msg_type: str, **kwargs):
        self.msg_queue.put(WorkerMessage(msg_type, kwargs))

    def _check_cancel(self) -> bool:
        return self._cancelled

    def run(self):
        try:
            if self.mode == "load":
                self._do_load()
            elif self.mode == "export":
                self._do_export()
        except Exception as e:
            self._post(WorkerMessage.TYPE_ERROR, message=str(e), traceback=traceback.format_exc())

    def _do_load(self):
        """Загружаем фид, парсим, фильтруем, отправляем список маршрутов в GUI."""
        self._post(WorkerMessage.TYPE_LOG, message="Начинаем загрузку фида...")

        # Берём первый enabled feed (пока поддерживаем один)
        feeds = [f for f in self.settings.feeds if f.enabled]
        if not feeds:
            raise RuntimeError("Нет активных источников фидов")
        feed = feeds[0]

        # Загрузка
        downloader = GTFSDownloader(
            feed_name=feed.name,
            feed_url=feed.url,
            timeout=self.settings.timeout_s,
            proxy=self.settings.proxy,
            user_agent=self.settings.user_agent,
            ttl_hours=self.settings.cache_ttl_hours,
        )
        zip_path, meta = downloader.download(force=self._force)
        self._post(WorkerMessage.TYPE_LOG, message=f"Фид загружен: {zip_path}")

        # Проверка свежести
        self._post(WorkerMessage.TYPE_PROGRESS, value=10, max_value=100)

        # Парсинг
        parser = GTFSParser(zip_path)
        parser.parse()
        self._parser = parser
        self._post(WorkerMessage.TYPE_PROGRESS, value=30, max_value=100)
        self._post(WorkerMessage.TYPE_LOG, message="GTFS распарсен")

        # Проверка актуальности фида
        checker = ActualityChecker(parser)
        freshness = checker.check_feed_freshness(meta)
        self._post(WorkerMessage.TYPE_LOG, message=freshness["message"])

        # Собираем маршруты
        routes_df = parser.build_routes_with_shapes()
        if routes_df.empty:
            raise RuntimeError("Не удалось построить маршруты — возможно, фид повреждён")

        self._post(WorkerMessage.TYPE_PROGRESS, value=50, max_value=100)

        # Фильтрация по настройкам
        routes_df = self._apply_filters(routes_df, checker)

        self._routes_df = routes_df
        self._post(WorkerMessage.TYPE_PROGRESS, value=90, max_value=100)

        # Формируем список для GUI
        route_list = []
        for _, row in routes_df.iterrows():
            # Пропускаем строки без геометрии (NaN)
            geom = row.get("geometry")
            if geom is None or pd.isna(geom) or geom.is_empty:
                continue
            
            num_points = row.get("num_points")
            length_m = row.get("length_m")
            
            route_list.append({
                "route_id": str(row.get("route_id", "")),
                "shape_id": str(row.get("shape_id", "")),
                "short_name": str(row.get("route_short_name", "")),
                "long_name": str(row.get("route_long_name", ""))[:60],
                "transport_type": str(row.get("transport_type", "")),
                "urban": str(row.get("urban", "")),
                "night": str(row.get("night", "")),
                "circular": str(row.get("circular", "")),
                "direction_id": str(row.get("direction_id", "")),
                "headsign": str(row.get("trip_headsign", ""))[:40],
                "num_points": int(num_points) if pd.notna(num_points) else 0,
                "length_m": float(length_m) if pd.notna(length_m) else 0.0,
            })

        self._post(WorkerMessage.TYPE_ROUTES_LOADED, routes=route_list, freshness=freshness)
        self._post(WorkerMessage.TYPE_PROGRESS, value=100, max_value=100)
        self._post(WorkerMessage.TYPE_DONE)

    def _apply_filters(self, routes_df: pd.DataFrame, checker: ActualityChecker) -> pd.DataFrame:
        """Применяем фильтры из настроек."""
        df = routes_df.copy()

        # Базовые фильтры
        if self.settings.transport_types:
            df = df[df["transport_type"].isin(self.settings.transport_types)]

        if self.settings.urban_mode == "urban":
            df = df[df["urban"] == "1"]
        elif self.settings.urban_mode == "suburban":
            df = df[df["urban"] == "0"]

        if not self.settings.include_night:
            df = df[df["night"] != "1"]

        if not self.settings.include_circular:
            df = df[df["circular"] != "1"]

        if self.settings.route_numbers.strip():
            allowed = self._parse_route_numbers(self.settings.route_numbers)
            df = df[df["route_short_name"].isin(allowed)]

        if self.settings.directions:
            df = df[df["direction_id"].astype(str).isin([str(d) for d in self.settings.directions])]

        # Фильтр по актуальности: оставляем ТОЛЬКО shape, используемые активными trip
        if self.settings.only_active:
            check_date = self._parse_date(self.settings.active_date) or date.today()
            active_services = checker.get_active_service_ids(check_date)
            trips = self._parser.get_df("trips")
            if trips is not None:
                # Фильтруем trips → только активные
                active_trips = trips[trips["service_id"].isin(active_services)]
                # Получаем shape_id, используемые активными trip
                active_shape_ids = set(active_trips["shape_id"].unique())
                # Оставляем в df только активные shape
                df = df[df["shape_id"].isin(active_shape_ids)]

        # Выбор основного shape
        if self.settings.shape_mode == "main":
            df = self._select_main_shape(df)
        elif self.settings.shape_mode == "longest":
            df = self._select_longest_shape(df)
        # "all" — ничего не делаем

        return df

    def _select_main_shape(self, df: pd.DataFrame) -> pd.DataFrame:
        """Оставляем shape с максимальным количеством точек на (route_id, direction_id)."""
        if df.empty:
            return df
        df = df.sort_values("num_points", ascending=False)
        return df.drop_duplicates(subset=["route_id", "direction_id"], keep="first")

    def _select_longest_shape(self, df: pd.DataFrame) -> pd.DataFrame:
        """Оставляем shape с максимальной длиной на (route_id, direction_id)."""
        if df.empty:
            return df
        df = df.sort_values("length_m", ascending=False)
        return df.drop_duplicates(subset=["route_id", "direction_id"], keep="first")

    def _parse_route_numbers(self, text: str) -> List[str]:
        """Парсим '3,7,10-15' в список строк."""
        result = []
        for part in text.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
                    for i in range(int(start), int(end) + 1):
                        result.append(str(i))
                except ValueError:
                    result.append(part)
            else:
                result.append(part)
        return result

    def _parse_date(self, text: str) -> Optional[date]:
        if not text:
            return None
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y%m%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _do_export(self):
        """Экспортируем выбранные маршруты в GPX."""
        if self._routes_df is None or self._routes_df.empty:
            raise RuntimeError("Нет данных для экспорта. Сначала загрузите фид.")

        self._post(WorkerMessage.TYPE_LOG, message="Начинаем экспорт...")
        self._post(WorkerMessage.TYPE_PROGRESS, value=10, max_value=100)

        # Фильтруем по выбранным shape_id (уникальный идентификатор варианта)
        selected = self._routes_df[self._routes_df["shape_id"].isin(self.selected_route_ids)]
        if selected.empty:
            raise RuntimeError("Не выбрано ни одного маршрута для экспорта")

        self._post(WorkerMessage.TYPE_PROGRESS, value=30, max_value=100)

        # Остановки
        stops_df = None
        if self.settings.include_stops:
            if self.settings.stops_source == "all":
                stops_df = self._parser.get_df("stops")
            else:
                # Получаем route_id из выбранных shape_id для привязки остановок
                selected_route_ids = selected["route_id"].unique().tolist()
                stops_df = self._parser.build_stops_for_routes(selected_route_ids)

        self._post(WorkerMessage.TYPE_PROGRESS, value=50, max_value=100)

        # GPX
        builder = GPXBuilder(
            track_name_template=self.settings.track_name_template,
            simplify=self.settings.simplify,
            simplify_tolerance_m=self.settings.simplify_tolerance_m,
            include_metadata=self.settings.include_metadata,
        )

        output_dir = Path(self.settings.output_dir) if self.settings.output_dir else Path.home() / "Documents"
        prefix = "routes"

        created = builder.export(
            routes_df=selected,
            stops_df=stops_df,
            output_dir=output_dir,
            prefix=prefix,
            output_single=self.settings.output_single,
            output_per_route=self.settings.output_per_route,
            stop_name_field=self.settings.stop_name_field,
        )

        self._post(WorkerMessage.TYPE_PROGRESS, value=100, max_value=100)
        self._post(WorkerMessage.TYPE_LOG, message=f"Экспорт завершён. Файлы: {', '.join(str(p.name) for p in created)}")
        self._post(WorkerMessage.TYPE_DONE, files=[str(p) for p in created])

    def set_parser_and_routes(self, parser: GTFSParser, routes_df: pd.DataFrame):
        """Устанавливаем parser и routes_df извне (для режима export после load)."""
        self._parser = parser
        self._routes_df = routes_df
