"""Парсинг GTFS CSV-файлов в pandas DataFrames."""
import zipfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from shapely.geometry import LineString


class GTFSParser:
    """Парсит GTFS ZIP в структурированные DataFrames."""

    def __init__(self, zip_path: Path):
        self.zip_path = zip_path
        self._dfs: Dict[str, pd.DataFrame] = {}
        self._calendar_dates_index: Optional[Dict] = None

    def _read_csv(self, name: str) -> Optional[pd.DataFrame]:
        """Читаем CSV из ZIP, если он есть."""
        try:
            with zipfile.ZipFile(self.zip_path, "r") as z:
                with z.open(name) as f:
                    return pd.read_csv(f, dtype=str, keep_default_na=False)
        except KeyError:
            return None
        except Exception as e:
            print(f"Ошибка чтения {name}: {e}")
            return None

    def parse(self) -> None:
        """Загружаем все доступные файлы GTFS."""
        files = [
            "agency", "routes", "trips", "shapes", "stops",
            "stop_times", "calendar", "calendar_dates", "feed_info",
            "frequencies", "operators", "operator_routes",
        ]
        for fname in files:
            df = self._read_csv(f"{fname}.txt")
            if df is not None:
                self._dfs[fname] = df

    def get_df(self, name: str) -> Optional[pd.DataFrame]:
        return self._dfs.get(name)

    def has_df(self, name: str) -> bool:
        return name in self._dfs

    def build_shapes(self) -> pd.DataFrame:
        """Собираем shapes.txt в LineString по shape_id."""
        shapes = self.get_df("shapes")
        if shapes is None or shapes.empty:
            return pd.DataFrame(columns=["shape_id", "geometry", "num_points", "length_m"])

        # Приводим типы
        shapes = shapes.copy()
        shapes["shape_pt_lat"] = pd.to_numeric(shapes["shape_pt_lat"], errors="coerce")
        shapes["shape_pt_lon"] = pd.to_numeric(shapes["shape_pt_lon"], errors="coerce")
        shapes["shape_pt_sequence"] = pd.to_numeric(shapes["shape_pt_sequence"], errors="coerce")
        shapes = shapes.dropna(subset=["shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"])

        # Сортируем и группируем
        shapes = shapes.sort_values(["shape_id", "shape_pt_sequence"])
        records = []
        for shape_id, group in shapes.groupby("shape_id", sort=False):
            coords = list(zip(group["shape_pt_lon"], group["shape_pt_lat"]))
            if len(coords) >= 2:
                line = LineString(coords)
                records.append({
                    "shape_id": shape_id,
                    "geometry": line,
                    "num_points": len(coords),
                    "length_m": line.length * 111_000,  # приблизительно в метрах
                })
            elif len(coords) == 1:
                # Точка — не трек, но сохраним
                records.append({
                    "shape_id": shape_id,
                    "geometry": LineString(coords + coords),
                    "num_points": 1,
                    "length_m": 0.0,
                })

        return pd.DataFrame(records)

    def build_routes_with_shapes(self) -> pd.DataFrame:
        """Связываем routes + trips + shapes."""
        routes = self.get_df("routes")
        trips = self.get_df("trips")
        shapes_geom = self.build_shapes()

        if routes is None or trips is None or shapes_geom.empty:
            return pd.DataFrame()

        # trips → shape_id (берём уникальные пары route_id + shape_id)
        cols = ["route_id", "shape_id", "direction_id"]
        if "trip_headsign" in trips.columns:
            cols.append("trip_headsign")
        trip_shapes = trips[cols].drop_duplicates()

        # Обогащаем shape_id геометрией
        trip_shapes = trip_shapes.merge(shapes_geom, on="shape_id", how="left")

        # Добавляем route info
        result = trip_shapes.merge(routes, on="route_id", how="left")
        return result

    def build_stops_for_routes(self, route_ids: Optional[list] = None) -> pd.DataFrame:
        """Остановки, привязанные к маршрутам (через stop_times → trips)."""
        stops = self.get_df("stops")
        stop_times = self.get_df("stop_times")
        trips = self.get_df("trips")

        if stops is None or stop_times is None or trips is None:
            return pd.DataFrame()

        # Фильтруем trips по route_ids
        if route_ids:
            trips = trips[trips["route_id"].isin(route_ids)]

        # Связываем
        merged = stop_times.merge(trips[["trip_id", "route_id"]], on="trip_id", how="inner")
        merged = merged.merge(stops, on="stop_id", how="left")
        # Уникальные остановки
        merged = merged.drop_duplicates(subset=["stop_id"])
        return merged

    def get_feed_info_dict(self) -> dict:
        """Возвращает feed_info как dict (первая строка)."""
        df = self.get_df("feed_info")
        if df is not None and not df.empty:
            return df.iloc[0].to_dict()
        return {}

    def index_calendar_dates(self) -> Dict[str, set]:
        """Индексируем calendar_dates для быстрой проверки."""
        if self._calendar_dates_index is not None:
            return self._calendar_dates_index

        df = self.get_df("calendar_dates")
        if df is None or df.empty:
            self._calendar_dates_index = {}
            return {}

        index: Dict[str, set] = {}
        for _, row in df.iterrows():
            sid = row["service_id"]
            date = row["date"]
            etype = row.get("exception_type", "1")
            key = f"{sid}:{date}"
            if key not in index:
                index[key] = set()
            index[key].add(etype)
        self._calendar_dates_index = index
        return index
