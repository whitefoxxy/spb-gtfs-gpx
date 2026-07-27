"""Проверка актуальности фида и маршрутов."""
from datetime import datetime, date
from typing import Dict, List, Optional, Set

import pandas as pd


class ActualityChecker:
    """Проверяет актуальность на двух уровнях: фид и маршрут."""

    def __init__(self, parser):
        self.parser = parser

    def check_feed_freshness(self, meta: dict) -> Dict:
        """
        Проверяем свежесть фида.
        Возвращает dict: {fresh: bool, message: str, days_old: int}
        """
        last_modified = meta.get("last_modified", "")
        if not last_modified:
            return {"fresh": False, "message": "Нет данных о дате фида", "days_old": -1}

        try:
            # Парсим HTTP-date
            lm_dt = datetime.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
            lm_dt = lm_dt.replace(tzinfo=None)
        except ValueError:
            try:
                lm_dt = datetime.strptime(last_modified, "%a, %d-%b-%Y %H:%M:%S %Z")
                lm_dt = lm_dt.replace(tzinfo=None)
            except ValueError:
                return {"fresh": False, "message": f"Неизвестный формат даты: {last_modified}", "days_old": -1}

        days_old = (datetime.now() - lm_dt).days
        if days_old <= 1:
            return {"fresh": True, "message": f"Фид свежий (обновлён {lm_dt.strftime('%d.%m.%Y')})", "days_old": days_old}
        elif days_old <= 3:
            return {"fresh": True, "message": f"Фид устарел на {days_old} дн.", "days_old": days_old}
        else:
            return {"fresh": False, "message": f"Фид устарел на {days_old} дн.!", "days_old": days_old}

    def get_active_service_ids(self, check_date: Optional[date] = None) -> Set[str]:
        """
        Возвращает service_id, активные на указанную дату.
        Учитывает calendar.txt и calendar_dates.txt.
        """
        if check_date is None:
            check_date = date.today()

        date_str = check_date.strftime("%Y%m%d")
        weekday = check_date.weekday()  # 0=понедельник
        weekday_cols = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        weekday_col = weekday_cols[weekday]

        active: Set[str] = set()

        # 1. calendar.txt
        cal = self.parser.get_df("calendar")
        if cal is not None and not cal.empty:
            for _, row in cal.iterrows():
                sid = row["service_id"]
                # Проверяем день недели
                if str(row.get(weekday_col, "0")) != "1":
                    continue
                # Проверяем диапазон дат
                start = str(row.get("start_date", ""))
                end = str(row.get("end_date", ""))
                if not start or not end:
                    continue
                # Защита от инвертированных дат (данные фида СПб имеют end_date в 2019)
                if start > end:
                    # Даты инвертированы — игнорируем диапазон, проверяем только день недели
                    active.add(sid)
                    continue
                if start <= date_str <= end:
                    active.add(sid)

        # 2. calendar_dates.txt — исключения
        cd_index = self.parser.index_calendar_dates()
        for key, etypes in cd_index.items():
            sid, d = key.split(":", 1)
            if d != date_str:
                continue
            # exception_type 1 = добавить, 2 = убрать
            if "1" in etypes:
                active.add(sid)
            if "2" in etypes:
                active.discard(sid)

        return active

    def check_route_actuality(self, route_id: str, active_services: Set[str]) -> bool:
        """Проверяем, есть ли у маршрута хотя бы один trip с активным service_id."""
        trips = self.parser.get_df("trips")
        if trips is None:
            return False
        route_trips = trips[trips["route_id"] == route_id]
        if route_trips.empty:
            return False
        services = set(route_trips["service_id"].unique())
        return bool(services & active_services)

    def get_route_actuality_map(self, route_ids: Optional[List[str]] = None, check_date: Optional[date] = None) -> Dict[str, bool]:
        """Возвращает {route_id: is_active} для всех или указанных маршрутов."""
        active_services = self.get_active_service_ids(check_date)
        routes = self.parser.get_df("routes")
        if routes is None:
            return {}

        if route_ids is None:
            route_ids = routes["route_id"].unique().tolist()

        result = {}
        for rid in route_ids:
            result[rid] = self.check_route_actuality(rid, active_services)
        return result
