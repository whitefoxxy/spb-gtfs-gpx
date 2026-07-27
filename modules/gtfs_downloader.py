"""Загрузка GTFS-фидов с кэшированием и условным GET."""
import json
import os
import time
import warnings
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Tuple

import requests
from urllib3.exceptions import InsecureRequestWarning

from .paths import get_feed_cache_dir

warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class GTFSDownloader:
    """Загружает GTFS ZIP, использует локальный кэш и условный GET."""

    def __init__(
        self,
        feed_name: str,
        feed_url: str,
        timeout: int = 120,
        proxy: str = "",
        user_agent: str = "spb-gtfs-gpx/1.0",
        ttl_hours: int = 24,
    ):
        self.feed_name = feed_name
        self.feed_url = feed_url
        self.timeout = timeout
        self.ttl_hours = ttl_hours
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        if proxy:
            self.session.proxies.update({"http": proxy, "https": proxy})

        self.cache_dir = get_feed_cache_dir(feed_name)
        self.zip_path = self.cache_dir / "feed.zip"
        self.meta_path = self.cache_dir / "meta.json"

    def _load_meta(self) -> dict:
        if self.meta_path.exists():
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_meta(self, meta: dict) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def _is_cache_fresh(self, meta: dict) -> bool:
        """Проверяем, не истёк ли TTL кэша."""
        downloaded_at = meta.get("downloaded_at")
        if not downloaded_at:
            return False
        try:
            dt = datetime.fromisoformat(downloaded_at)
            age_hours = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            return age_hours < self.ttl_hours
        except Exception:
            return False

    def _conditional_headers(self, meta: dict) -> dict:
        """Формируем заголовки для условного GET."""
        headers = {}
        last_modified = meta.get("last_modified")
        etag = meta.get("etag")
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        if etag:
            headers["If-None-Match"] = etag
        return headers

    def download(self, force: bool = False) -> Tuple[Path, dict]:
        """
        Возвращает путь к ZIP и словарь с информацией о фиде.
        Если force=True — игнорируем кэш и качаем заново.
        """
        meta = self._load_meta()

        # Если кэш свежий и не force — используем его
        if not force and self.zip_path.exists() and self._is_cache_fresh(meta):
            return self.zip_path, meta

        headers = self._conditional_headers(meta) if not force else {}

        try:
            resp = self.session.get(
                self.feed_url,
                headers=headers,
                timeout=self.timeout,
                stream=True,
            )
        except requests.exceptions.SSLError:
            # Fallback: отключаем проверку SSL
            resp = self.session.get(
                self.feed_url,
                headers=headers,
                timeout=self.timeout,
                stream=True,
                verify=False,
            )
        except requests.RequestException as e:
            # Если сеть недоступна, но есть кэш — используем его
            if self.zip_path.exists():
                return self.zip_path, meta
            raise RuntimeError(f"Ошибка загрузки {self.feed_name}: {e}") from e

        if resp.status_code == 304:
            # Не изменился
            meta["downloaded_at"] = datetime.now(timezone.utc).isoformat()
            self._save_meta(meta)
            return self.zip_path, meta

        if resp.status_code != 200:
            if self.zip_path.exists():
                return self.zip_path, meta
            raise RuntimeError(
                f"Ошибка загрузки {self.feed_name}: HTTP {resp.status_code}"
            )

        # Сохраняем ZIP
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.zip_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)

        # Обновляем meta
        meta = {
            "last_modified": resp.headers.get("Last-Modified", ""),
            "etag": resp.headers.get("ETag", ""),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "content_length": resp.headers.get("Content-Length", ""),
            "url": self.feed_url,
        }
        self._save_meta(meta)
        return self.zip_path, meta

    def get_feed_info(self) -> dict:
        """Возвращает meta без загрузки."""
        return self._load_meta()
