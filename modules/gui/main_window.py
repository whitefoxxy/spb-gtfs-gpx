"""Главное окно приложения."""
import queue
import tkinter
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import customtkinter as ctk

from ..settings import Settings, FeedSource
from ..gtfs_parser import GTFSParser
from .worker import GTFSWorker, WorkerMessage
from .widgets import SearchableRouteList, LabeledEntry, LabeledComboBox


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """Главное окно приложения GTFS → GPX."""

    def __init__(self):
        super().__init__()
        self.title("GTFS → GPX: Маршруты СПб")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        self.settings = Settings.load()
        self._worker: Optional[GTFSWorker] = None
        self._msg_queue: queue.Queue = queue.Queue()
        self._parser: Optional[GTFSParser] = None
        self._routes_df = None
        self._raw_routes_df = None
        self._after_id: Optional[str] = None

        self._build_ui()
        self._apply_settings_to_ui()
        self._start_queue_polling()

    def _build_ui(self):
        # === ВЕРХНЯЯ ПАНЕЛЬ ===
        self.header = ctk.CTkFrame(self, height=50)
        self.header.pack(fill="x", padx=10, pady=(10, 0))
        self.header.pack_propagate(False)

        self.status_label = ctk.CTkLabel(self.header, text="Готов к работе", anchor="w")
        self.status_label.pack(side="left", padx=10, pady=5)

        self.btn_refresh = ctk.CTkButton(self.header, text="🔄 Обновить фид", command=self._on_refresh)
        self.btn_refresh.pack(side="right", padx=5, pady=5)

        self.btn_filter = ctk.CTkButton(self.header, text="🔍 Применить фильтр", command=self._on_apply_filter)
        self.btn_filter.pack(side="right", padx=5, pady=5)

        self.btn_load = ctk.CTkButton(self.header, text="📥 Загрузить маршруты", command=self._on_load)
        self.btn_load.pack(side="right", padx=5, pady=5)

        # === ОСНОВНАЯ ОБЛАСТЬ ===
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.main_frame.grid_columnconfigure(1, weight=3)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(2, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # --- ЛЕВАЯ ПАНЕЛЬ: Фильтры ---
        self.left_panel = ctk.CTkScrollableFrame(self.main_frame, label_text="Фильтры")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Регион
        ctk.CTkLabel(self.left_panel, text="Источник фида:", anchor="w").pack(fill="x", padx=5, pady=(5, 0))
        self.feed_combo = ctk.CTkComboBox(self.left_panel, values=[], state="readonly")
        self.feed_combo.pack(fill="x", padx=5, pady=5)

        # Тип транспорта
        ctk.CTkLabel(self.left_panel, text="Тип транспорта:", anchor="w").pack(fill="x", padx=5, pady=(10, 0))
        self.chk_bus = ctk.CTkCheckBox(self.left_panel, text="Автобус")
        self.chk_bus.pack(fill="x", padx=5, pady=2)
        self.chk_trolley = ctk.CTkCheckBox(self.left_panel, text="Троллейбус")
        self.chk_trolley.pack(fill="x", padx=5, pady=2)
        self.chk_tram = ctk.CTkCheckBox(self.left_panel, text="Трамвай")
        self.chk_tram.pack(fill="x", padx=5, pady=2)

        # Номера маршрутов
        self.entry_numbers = LabeledEntry(self.left_panel, label="Номера:", width=150)
        self.entry_numbers.pack(fill="x", padx=5, pady=(10, 5))

        # Направление
        ctk.CTkLabel(self.left_panel, text="Направление:", anchor="w").pack(fill="x", padx=5, pady=(5, 0))
        self.chk_dir0 = ctk.CTkCheckBox(self.left_panel, text="Прямое")
        self.chk_dir0.pack(fill="x", padx=5, pady=2)
        self.chk_dir1 = ctk.CTkCheckBox(self.left_panel, text="Обратное")
        self.chk_dir1.pack(fill="x", padx=5, pady=2)

        # Городские/пригородные
        ctk.CTkLabel(self.left_panel, text="Территория:", anchor="w").pack(fill="x", padx=5, pady=(10, 0))
        self.urban_combo = ctk.CTkComboBox(self.left_panel, values=["Все", "Городские", "Пригородные"], state="readonly")
        self.urban_combo.pack(fill="x", padx=5, pady=5)

        # Ночные / кольцевые
        self.chk_night = ctk.CTkCheckBox(self.left_panel, text="Ночные маршруты")
        self.chk_night.pack(fill="x", padx=5, pady=(5, 2))
        self.chk_circular = ctk.CTkCheckBox(self.left_panel, text="Кольцевые")
        self.chk_circular.pack(fill="x", padx=5, pady=2)

        # Дата актуальности
        self.entry_date = LabeledEntry(self.left_panel, label="Дата (ГГГГ-ММ-ДД):", width=120)
        self.entry_date.pack(fill="x", padx=5, pady=(10, 5))
        self.chk_only_active = ctk.CTkCheckBox(self.left_panel, text="Только действующие")
        self.chk_only_active.pack(fill="x", padx=5, pady=2)

        # --- ЦЕНТРАЛЬНАЯ ПАНЕЛЬ: Список маршрутов ---
        self.center_panel = ctk.CTkFrame(self.main_frame)
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.center_panel.grid_rowconfigure(0, weight=1)
        self.center_panel.grid_columnconfigure(0, weight=1)

        self.route_list = SearchableRouteList(self.center_panel)
        self.route_list.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # --- ПРАВАЯ ПАНЕЛЬ: Опции вывода ---
        self.right_panel = ctk.CTkScrollableFrame(self.main_frame, label_text="Опции вывода")
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)

        # Shape
        ctk.CTkLabel(self.right_panel, text="Вариант трека:", anchor="w").pack(fill="x", padx=5, pady=(5, 0))
        self.shape_combo = ctk.CTkComboBox(
            self.right_panel,
            values=["Основной (max точек)", "Все", "Длиннейший"],
            state="readonly",
        )
        self.shape_combo.pack(fill="x", padx=5, pady=5)

        # Остановки
        self.chk_stops = ctk.CTkCheckBox(self.right_panel, text="Включить остановки")
        self.chk_stops.pack(fill="x", padx=5, pady=(10, 2))
        self.stops_source_combo = ctk.CTkComboBox(
            self.right_panel,
            values=["Все города", "Только выбранные маршруты"],
            state="readonly",
        )
        self.stops_source_combo.pack(fill="x", padx=5, pady=5)
        self.stop_name_combo = ctk.CTkComboBox(
            self.right_panel,
            values=["stop_name", "stop_code", "stop_id"],
            state="readonly",
        )
        self.stop_name_combo.pack(fill="x", padx=5, pady=5)

        # GPX вывод
        ctk.CTkLabel(self.right_panel, text="Файлы GPX:", anchor="w").pack(fill="x", padx=5, pady=(10, 0))
        self.chk_single = ctk.CTkCheckBox(self.right_panel, text="Один общий файл")
        self.chk_single.pack(fill="x", padx=5, pady=2)
        self.chk_per_route = ctk.CTkCheckBox(self.right_panel, text="Отдельно по маршрутам")
        self.chk_per_route.pack(fill="x", padx=5, pady=2)
        self.chk_merge = ctk.CTkCheckBox(self.right_panel, text="Объединить в один трек")
        self.chk_merge.pack(fill="x", padx=5, pady=2)

        # Папка вывода
        self.entry_output = LabeledEntry(self.right_panel, label="Папка:", width=150)
        self.entry_output.pack(fill="x", padx=5, pady=(10, 5))
        ctk.CTkButton(self.right_panel, text="Выбрать папку", command=self._on_browse_output).pack(fill="x", padx=5, pady=5)

        # Шаблон имени
        self.entry_template = LabeledEntry(self.right_panel, label="Шаблон трека:", width=150)
        self.entry_template.pack(fill="x", padx=5, pady=(10, 5))

        # Упрощение
        self.chk_simplify = ctk.CTkCheckBox(self.right_panel, text="Упростить геометрию (RDP)")
        self.chk_simplify.pack(fill="x", padx=5, pady=(10, 2))
        self.entry_tolerance = LabeledEntry(self.right_panel, label="Толерантность (м):", width=80)
        self.entry_tolerance.pack(fill="x", padx=5, pady=5)

        # Метаданные
        self.chk_metadata = ctk.CTkCheckBox(self.right_panel, text="Включить метаданные")
        self.chk_metadata.pack(fill="x", padx=5, pady=(10, 2))

        # === НИЖНЯЯ ПАНЕЛЬ ===
        self.bottom = ctk.CTkFrame(self)
        self.bottom.pack(fill="x", padx=10, pady=(0, 10))

        self.progress = ctk.CTkProgressBar(self.bottom)
        self.progress.pack(fill="x", padx=10, pady=(5, 0))
        self.progress.set(0)

        self.log_text = ctk.CTkTextbox(self.bottom, height=80, state="disabled")
        self.log_text.pack(fill="x", padx=10, pady=5)

        self.btn_export = ctk.CTkButton(self.bottom, text="▶ Экспорт в GPX", command=self._on_export)
        self.btn_export.pack(side="right", padx=10, pady=5)

    def _apply_settings_to_ui(self):
        """Загружаем сохранённые настройки в UI."""
        s = self.settings

        # Feeds
        feed_names = [f.name for f in s.feeds]
        self.feed_combo.configure(values=feed_names)
        if feed_names:
            self.feed_combo.set(feed_names[0])

        # Transport types
        self.chk_bus.select() if "bus" in s.transport_types else self.chk_bus.deselect()
        self.chk_trolley.select() if "trolley" in s.transport_types else self.chk_trolley.deselect()
        self.chk_tram.select() if "tram" in s.transport_types else self.chk_tram.deselect()

        # Route numbers
        self.entry_numbers.set(s.route_numbers)

        # Directions
        self.chk_dir0.select() if 0 in s.directions else self.chk_dir0.deselect()
        self.chk_dir1.select() if 1 in s.directions else self.chk_dir1.deselect()

        # Urban
        urban_map = {"all": "Все", "urban": "Городские", "suburban": "Пригородные"}
        self.urban_combo.set(urban_map.get(s.urban_mode, "Все"))

        # Night / circular
        self.chk_night.select() if s.include_night else self.chk_night.deselect()
        self.chk_circular.select() if s.include_circular else self.chk_circular.deselect()

        # Date
        self.entry_date.set(s.active_date or date.today().strftime("%Y-%m-%d"))
        self.chk_only_active.select() if s.only_active else self.chk_only_active.deselect()

        # Shape
        shape_map = {"main": "Основной (max точек)", "all": "Все", "longest": "Длиннейший"}
        self.shape_combo.set(shape_map.get(s.shape_mode, "Основной (max точек)"))

        # Stops
        self.chk_stops.select() if s.include_stops else self.chk_stops.deselect()
        stops_src_map = {"all": "Все города", "selected": "Только выбранные маршруты"}
        self.stops_source_combo.set(stops_src_map.get(s.stops_source, "Только выбранные маршруты"))
        self.stop_name_combo.set(s.stop_name_field)

        # Output
        self.chk_single.select() if s.output_single else self.chk_single.deselect()
        self.chk_per_route.select() if s.output_per_route else self.chk_per_route.deselect()
        self.chk_merge.select() if s.merge_routes else self.chk_merge.deselect()
        self.entry_output.set(s.output_dir or str(Path.home() / "Documents"))
        self.entry_template.set(s.track_name_template)

        # Simplify
        self.chk_simplify.select() if s.simplify else self.chk_simplify.deselect()
        self.entry_tolerance.set(str(s.simplify_tolerance_m))

        # Metadata
        self.chk_metadata.select() if s.include_metadata else self.chk_metadata.deselect()

    def _collect_settings_from_ui(self) -> Settings:
        """Собираем настройки из UI."""
        s = self.settings

        # Transport types
        types = []
        if self.chk_bus.get():
            types.append("bus")
        if self.chk_trolley.get():
            types.append("trolley")
        if self.chk_tram.get():
            types.append("tram")
        s.transport_types = types

        s.route_numbers = self.entry_numbers.get()

        dirs = []
        if self.chk_dir0.get():
            dirs.append(0)
        if self.chk_dir1.get():
            dirs.append(1)
        s.directions = dirs

        urban_map = {"Все": "all", "Городские": "urban", "Пригородные": "suburban"}
        s.urban_mode = urban_map.get(self.urban_combo.get(), "all")

        s.include_night = bool(self.chk_night.get())
        s.include_circular = bool(self.chk_circular.get())

        s.active_date = self.entry_date.get()
        s.only_active = bool(self.chk_only_active.get())

        shape_map = {"Основной (max точек)": "main", "Все": "all", "Длиннейший": "longest"}
        s.shape_mode = shape_map.get(self.shape_combo.get(), "main")

        s.include_stops = bool(self.chk_stops.get())
        stops_src_map = {"Все города": "all", "Только выбранные маршруты": "selected"}
        s.stops_source = stops_src_map.get(self.stops_source_combo.get(), "selected")
        s.stop_name_field = self.stop_name_combo.get()

        s.output_single = bool(self.chk_single.get())
        s.output_per_route = bool(self.chk_per_route.get())
        s.merge_routes = bool(self.chk_merge.get())
        s.output_dir = self.entry_output.get()
        s.track_name_template = self.entry_template.get()

        s.simplify = bool(self.chk_simplify.get())
        try:
            s.simplify_tolerance_m = float(self.entry_tolerance.get())
        except ValueError:
            s.simplify_tolerance_m = 20.0

        s.include_metadata = bool(self.chk_metadata.get())

        return s

    def _on_browse_output(self):
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            self.entry_output.set(folder)

    def _on_load(self):
        s = self._collect_settings_from_ui()
        s.save()
        self.settings = s

        self._set_busy(True)
        self.log("Загрузка маршрутов...")
        self.progress.set(0)

        self._worker = GTFSWorker(settings=s, message_queue=self._msg_queue, mode="load")
        self._worker.start()

    def _on_refresh(self):
        """Принудительное обновление фида."""
        s = self._collect_settings_from_ui()
        s.save()
        self.settings = s
        self._set_busy(True)
        self.log("Принудительное обновление фида...")
        self.progress.set(0)
        self._worker = GTFSWorker(settings=s, message_queue=self._msg_queue, mode="load", force=True)
        self._worker.start()

    def _on_apply_filter(self):
        """Применяем фильтры к уже загруженному фиду (без повторной загрузки)."""
        if self._parser is None or self._raw_routes_df is None:
            self._show_error("Сначала загрузите фид (кнопка «Загрузить маршруты»)")
            return

        s = self._collect_settings_from_ui()
        s.save()
        self.settings = s

        self._set_busy(True)
        self.log("Применение фильтров...")
        self.progress.set(0)

        self._worker = GTFSWorker(settings=s, message_queue=self._msg_queue, mode="filter")
        self._worker.set_raw_data(self._parser, self._raw_routes_df)
        self._worker.start()

    def _on_export(self):
        selected = self.route_list.get_selected_ids()
        if not selected:
            self._show_error("Не выбрано ни одного маршрута")
            return

        s = self._collect_settings_from_ui()
        s.save()
        self.settings = s

        self._set_busy(True)
        self.log(f"Экспорт {len(selected)} маршрутов...")
        self.progress.set(0)

        self._worker = GTFSWorker(
            settings=s,
            message_queue=self._msg_queue,
            mode="export",
            selected_route_ids=selected,
        )
        # Передаём parser и routes_df из предыдущей загрузки
        if self._parser is not None and self._routes_df is not None:
            self._worker.set_parser_and_routes(self._parser, self._routes_df)
        self._worker.start()

    def _start_queue_polling(self):
        """Опрос очереди сообщений из worker."""
        self._process_queue()

    def _process_queue(self):
        try:
            while True:
                msg = self._msg_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        self._after_id = self.after(100, self._process_queue)

    def _handle_message(self, msg: WorkerMessage):
        if msg.type == WorkerMessage.TYPE_PROGRESS:
            val = msg.data.get("value", 0)
            max_val = msg.data.get("max_value", 100)
            self.progress.set(val / max_val)
        elif msg.type == WorkerMessage.TYPE_LOG:
            self.log(msg.data.get("message", ""))
        elif msg.type == WorkerMessage.TYPE_ROUTES_LOADED:
            routes = msg.data.get("routes", [])
            freshness = msg.data.get("freshness", {})
            self.route_list.load_routes(routes)
            self.status_label.configure(
                text=f"Загружено маршрутов: {len(routes)} | {freshness.get('message', '')}"
            )
            # Копируем parser и routes_df из worker для экспорта и фильтрации
            if self._worker is not None:
                self._parser = self._worker._parser
                self._routes_df = self._worker._routes_df
                self._raw_routes_df = self._worker._raw_routes_df
        elif msg.type == WorkerMessage.TYPE_DONE:
            self._set_busy(False)
            files = msg.data.get("files", [])
            if files:
                self.log(f"Готово! Созданы файлы: {', '.join(files)}")
        elif msg.type == WorkerMessage.TYPE_ERROR:
            self._set_busy(False)
            self.log(f"ОШИБКА: {msg.data.get('message', '')}")
            self._show_error(msg.data.get("message", "Неизвестная ошибка"))

    def log(self, text: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{text}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_load.configure(state=state)
        self.btn_refresh.configure(state=state)
        self.btn_filter.configure(state=state)
        self.btn_export.configure(state=state)

    def _show_error(self, message: str):
        import tkinter.messagebox as mb
        mb.showerror("Ошибка", message)

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        if self._worker and self._worker.is_alive():
            self._worker.cancel()
            self._worker.join(timeout=2)
        super().destroy()
