"""Генерация GPX-файлов из GTFS-данных."""
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import gpxpy
import gpxpy.gpx
import pandas as pd
from shapely.geometry import LineString


class GPXBuilder:
    """Строит GPX из отфильтрованных маршрутов и остановок."""

    def __init__(
        self,
        track_name_template: str = "{short_name} {headsign}",
        simplify: bool = False,
        simplify_tolerance_m: float = 20.0,
        include_metadata: bool = True,
    ):
        self.track_name_template = track_name_template
        self.simplify = simplify
        self.simplify_tolerance_m = simplify_tolerance_m
        self.include_metadata = include_metadata

    def _build_track_name(self, row: pd.Series) -> str:
        """Формируем имя трека по шаблону."""
        template = self.track_name_template
        # Доступные переменные
        short_name = str(row.get("route_short_name", ""))
        headsign = str(row.get("trip_headsign", ""))
        if not headsign:
            headsign = str(row.get("route_long_name", ""))
        route_id = str(row.get("route_id", ""))
        direction = str(row.get("direction_id", ""))
        route_long = str(row.get("route_long_name", ""))

        name = template
        name = name.replace("{short_name}", short_name)
        name = name.replace("{headsign}", headsign)
        name = name.replace("{route_id}", route_id)
        name = name.replace("{direction}", direction)
        name = name.replace("{route_long_name}", route_long)
        return name.strip() or f"Маршрут {short_name}"

    def _simplify_line(self, line: LineString) -> LineString:
        """Упрощаем LineString методом RDP (shapely)."""
        if not self.simplify or line.is_empty:
            return line
        # tolerance в градусах (приблизительно: 1° ≈ 111 км)
        tol_deg = self.simplify_tolerance_m / 111_000
        simplified = line.simplify(tol_deg, preserve_topology=False)
        if simplified.is_empty or len(simplified.coords) < 2:
            return line
        return simplified

    def _line_to_track(self, line: LineString, name: str, desc: str = "") -> gpxpy.gpx.GPXTrack:
        """Преобразуем LineString в GPXTrack."""
        track = gpxpy.gpx.GPXTrack(name=name, description=desc)
        segment = gpxpy.gpx.GPXTrackSegment()
        for lon, lat in line.coords:
            segment.points.append(gpxpy.gpx.GPXTrackPoint(latitude=lat, longitude=lon))
        track.segments.append(segment)
        return track

    def _stop_to_wpt(self, row: pd.Series, name_field: str = "stop_name") -> gpxpy.gpx.GPXWaypoint:
        """Преобразуем остановку в GPXWaypoint."""
        lat = float(row.get("stop_lat", 0))
        lon = float(row.get("stop_lon", 0))
        name = str(row.get(name_field, row.get("stop_name", "")))
        desc = str(row.get("stop_name", ""))
        return gpxpy.gpx.GPXWaypoint(latitude=lat, longitude=lon, name=name, description=desc)

    def build_gpx(
        self,
        routes_df: pd.DataFrame,
        stops_df: Optional[pd.DataFrame] = None,
        stop_name_field: str = "stop_name",
    ) -> gpxpy.gpx.GPX:
        """Собираем один GPX-объект из маршрутов и остановок."""
        gpx = gpxpy.gpx.GPX()

        if self.include_metadata:
            gpx.name = "Маршруты общественного транспорта"
            gpx.description = f"Сгенерировано {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            gpx.time = datetime.now()

        # Треки
        for _, row in routes_df.iterrows():
            geom = row.get("geometry")
            if geom is None or geom.is_empty:
                continue
            line = self._simplify_line(geom)
            name = self._build_track_name(row)
            desc = str(row.get("route_long_name", ""))
            track = self._line_to_track(line, name, desc)
            gpx.tracks.append(track)

        # Waypoints (остановки)
        if stops_df is not None and not stops_df.empty:
            for _, row in stops_df.iterrows():
                try:
                    wpt = self._stop_to_wpt(row, stop_name_field)
                    gpx.waypoints.append(wpt)
                except Exception:
                    continue

        return gpx

    def export(
        self,
        routes_df: pd.DataFrame,
        stops_df: Optional[pd.DataFrame] = None,
        output_dir: Path = Path("."),
        prefix: str = "routes",
        output_single: bool = True,
        output_per_route: bool = False,
        stop_name_field: str = "stop_name",
    ) -> List[Path]:
        """
        Экспортируем GPX в файл(ы).
        Возвращает список созданных путей.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        created: List[Path] = []

        if output_single:
            gpx = self.build_gpx(routes_df, stops_df, stop_name_field)
            path = output_dir / f"{prefix}.gpx"
            with open(path, "w", encoding="utf-8") as f:
                f.write(gpx.to_xml())
            created.append(path)

        if output_per_route:
            # Группируем по route_id
            for route_id, group in routes_df.groupby("route_id", sort=False):
                gpx = self.build_gpx(group, None, stop_name_field)
                short_name = str(group.iloc[0].get("route_short_name", route_id))
                # Очищаем имя файла
                safe_name = re.sub(r'[^\w\-_.]', '_', short_name)
                path = output_dir / f"{prefix}_{safe_name}.gpx"
                with open(path, "w", encoding="utf-8") as f:
                    f.write(gpx.to_xml())
                created.append(path)

        return created
