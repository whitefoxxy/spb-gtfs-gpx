"""Вспомогательные виджеты CustomTkinter."""
from typing import Callable, Dict, List, Optional

import customtkinter as ctk


class SearchableRouteList(ctk.CTkFrame):
    """Список маршрутов с поиском и чекбоксами."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        self.search_entry = ctk.CTkEntry(self, placeholder_text="Поиск маршрута...", textvariable=self.search_var)
        self.search_entry.pack(fill="x", padx=5, pady=5)

        # Скроллируемый фрейм для чекбоксов
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Маршруты")
        self.scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Кнопки выбора
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=5, pady=5)
        ctk.CTkButton(btn_frame, text="Все", width=60, command=self.select_all).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Никто", width=60, command=self.select_none).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="Инвертировать", width=100, command=self.invert_selection).pack(side="left", padx=2)

        self._routes: List[dict] = []
        self._checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self._vars: Dict[str, ctk.BooleanVar] = {}
        self._shape_ids: Dict[str, str] = {}  # key -> shape_id
        self._on_change: Optional[Callable] = None
        self._search_after_id: Optional[str] = None

    def set_on_change(self, callback: Callable):
        self._on_change = callback

    def load_routes(self, routes: List[dict]):
        """Загружаем список маршрутов — создаём чекбоксы один раз."""
        # Очищаем старые чекбоксы
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self._checkboxes.clear()
        self._vars.clear()
        self._shape_ids.clear()

        self._routes = routes

        # Создаём все чекбоксы один раз (ключ — индекс, т.к. route_id может дублироваться)
        for i, route in enumerate(routes):
            key = str(i)
            shape_id = route.get("shape_id", str(i))
            self._shape_ids[key] = shape_id

            var = ctk.BooleanVar(value=False)
            var.trace_add("write", lambda *_args, _key=key: self._notify_change(_key))
            self._vars[key] = var

            short = route.get("short_name", "")
            long_name = route.get("long_name", "")
            headsign = route.get("headsign", "")
            urban = "🌆" if route.get("urban") == "1" else "🌲"
            night = "🌙" if route.get("night") == "1" else ""
            text = f"{urban} {short} {night} | {long_name[:35]}"
            if headsign:
                text += f" → {headsign[:25]}"

            cb = ctk.CTkCheckBox(self.scroll_frame, text=text, variable=var)
            cb.pack(fill="x", padx=2, pady=1)
            self._checkboxes[key] = cb

    def _on_search(self, *_args):
        """Debounce: ждём 300мс после последнего нажатия."""
        if self._search_after_id:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(300, self._apply_filter)

    def _apply_filter(self):
        """Фильтруем видимые чекбоксы через pack/pack_forget (без destroy/create)."""
        self._search_after_id = None
        query = self.search_var.get().lower().strip()

        for i, route in enumerate(self._routes):
            key = str(i)
            cb = self._checkboxes.get(key)
            if cb is None:
                continue

            if not query:
                cb.pack(fill="x", padx=2, pady=1)
                continue

            # Проверяем совпадение
            short = str(route.get("short_name", "")).lower()
            long_name = str(route.get("long_name", "")).lower()
            headsign = str(route.get("headsign", "")).lower()

            if query in short or query in long_name or query in headsign:
                cb.pack(fill="x", padx=2, pady=1)
            else:
                cb.pack_forget()

    def _notify_change(self, key: str):
        if self._on_change:
            sid = self._shape_ids.get(key, "")
            self._on_change(sid, self._vars.get(key, ctk.BooleanVar()).get())

    def select_all(self):
        for var in self._vars.values():
            var.set(True)

    def select_none(self):
        for var in self._vars.values():
            var.set(False)

    def invert_selection(self):
        for var in self._vars.values():
            var.set(not var.get())

    def get_selected_ids(self) -> List[str]:
        selected = []
        for key, var in self._vars.items():
            if var.get():
                selected.append(self._shape_ids.get(key, ""))
        return selected

    def set_selected_ids(self, ids: List[str]):
        id_set = set(ids)
        for key, var in self._vars.items():
            var.set(self._shape_ids.get(key, "") in id_set)


class LabeledEntry(ctk.CTkFrame):
    """Поле ввода с меткой."""

    def __init__(self, master, label: str, default: str = "", width: int = 200, **kwargs):
        super().__init__(master, **kwargs)
        self.label = ctk.CTkLabel(self, text=label, width=120, anchor="w")
        self.label.pack(side="left", padx=5)
        self.entry = ctk.CTkEntry(self, width=width)
        self.entry.insert(0, default)
        self.entry.pack(side="left", padx=5, fill="x", expand=True)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)


class LabeledComboBox(ctk.CTkFrame):
    """Выпадающий список с меткой."""

    def __init__(self, master, label: str, values: List[str], default: str = None, width: int = 200, **kwargs):
        super().__init__(master, **kwargs)
        self.label = ctk.CTkLabel(self, text=label, width=120, anchor="w")
        self.label.pack(side="left", padx=5)
        self.combo = ctk.CTkComboBox(self, values=values, width=width)
        if default and default in values:
            self.combo.set(default)
        elif values:
            self.combo.set(values[0])
        self.combo.pack(side="left", padx=5, fill="x", expand=True)

    def get(self) -> str:
        return self.combo.get()

    def set(self, value: str):
        self.combo.set(value)
