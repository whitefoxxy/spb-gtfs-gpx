# История разработки GTFS → GPX конвертера

## Проект

**Репозиторий:** https://github.com/whitefoxxy/spb-gtfs-gpx  
**Назначение:** GUI-приложение для загрузки GTFS-фидов общественного транспорта СПб и конвертации маршрутов в формат GPX  
**Стек:** Python 3.10+, CustomTkinter, pandas, gpxpy, shapely, requests

---

## Этап 1. Планирование и исследование

### Анализ источника данных
- GTFS-фид СПб: `https://transport.orgp.spb.ru/Portal/transport/internalapi/gtfs/feed.zip`
- Размер: ~35 МБ, обновляется ежедневно (~00:24 МСК)
- Содержит 544 маршрута, 8657 остановок, 128K рейсов

### Структура GTFS-фида СПб
| Файл | Строк | Особенности |
|---|---|---|
| `routes.txt` | 544 | Доп. поля: `transport_type`, `urban`, `night`, `circular` |
| `trips.txt` | 128 091 | Нет `trip_headsign` |
| `shapes.txt` | — | Геометрия маршрутов |
| `stops.txt` | 8 657 | Остановки |
| `calendar.txt` | 1 005 | **Инвертированные даты** (start=2026, end=2019) |
| `calendar_dates.txt` | 314 890 | Исключения расписания |
| `feed_info.txt` | 1 | Нет `feed_end_date` |

### Ключевые находки
- `route_type=3` используется и для автобусов, и для троллейбусов — различение по полю `transport_type`
- Ленинградская область: отдельного GTFS-фида нет, но SPb-фид содержит 99 пригородных маршрутов с LO-населёнными пунктами
- `feed_info.txt` не содержит дат — актуальность фида проверяем по HTTP `Last-Modified`

---

## Этап 2. Реализация

### Структура проекта
```
spb_gtfs_gpx/
├── main.py                  # Точка входа
├── build.spec               # PyInstaller spec
├── requirements.txt         # Зависимости
├── install.ps1              # Установщик Windows
├── install.sh               # Установщик Linux/macOS
├── README.md                # Документация
├── .gitignore
└── modules/
    ├── __init__.py
    ├── paths.py             # Кроссплатформенные пути
    ├── settings.py          # Настройки + config.json
    ├── gtfs_downloader.py   # Загрузка + кэш
    ├── gtfs_parser.py       # Парсинг CSV
    ├── actuality_checker.py # Проверка актуальности
    ├── gpx_builder.py       # Генерация GPX
    └── gui/
        ├── __init__.py
        ├── main_window.py   # Главное окно
        ├── widgets.py       # Виджеты
        └── worker.py        # Фоновый поток
```

### Модули

#### `paths.py`
- Кроссплатформенные пути через `platformdirs`
- Config: `%APPDATA%` (Win), `~/Library/Application Support` (Mac), `~/.config` (Linux)
- Cache: `%LOCALAPPDATA%` (Win), `~/Library/Caches` (Mac), `~/.cache` (Linux)
- Fallback на `Path.home()` если `platformdirs` недоступен

#### `settings.py`
- Dataclass `Settings` с 20+ настройками
- Dataclass `FeedSource` для источников GTFS
- Преднастроенный источник: Санкт-Петербург
- Автосохранение/загрузка в `config.json`

#### `gtfs_downloader.py`
- Загрузка ZIP с условным GET (`If-Modified-Since` / `If-None-Match`)
- Локальный кэш: `feed.zip` + `meta.json`
- TTL кэша (по умолчанию 24 часа)
- Fallback на `verify=False` при SSL-ошибке
- Поддержка прокси и User-Agent

#### `gtfs_parser.py`
- Чтение всех CSV из ZIP в pandas DataFrames
- Сборка `LineString` из `shapes.txt`
- Связывание routes + trips + shapes
- Привязка остановок к маршрутам через `stop_times`
- Индексирование `calendar_dates.txt` для быстрой проверки

#### `actuality_checker.py`
- Проверка свежести фида по HTTP `Last-Modified`
- Проверка активности маршрутов по `calendar.txt` + `calendar_dates.txt`
- Защита от инвертированных дат (игнорирование диапазона при инверсии)

#### `gpx_builder.py`
- Генерация GPX через `gpxpy`
- Треки (`<trk>`) из shapes
- Waypoints (`<wpt>`) из остановок
- Упрощение геометрии (RDP через `shapely.simplify`)
- Шаблоны имён треков
- Метаданные GPX
- Экспорт: один файл и/или по маршрутам

#### `gui/worker.py`
- Фоновый поток (`threading.Thread`)
- Режимы: `load` (загрузка) и `export` (экспорт)
- Очередь сообщений для GUI (прогресс, лог, ошибки)
- Фильтрация: transport_type, urban, night, circular, номера, направление, актуальность
- Выбор shape: основной (max точек) / все / длиннейший
- Принудительное обновление (`force=True`)

#### `gui/widgets.py`
- `SearchableRouteList` — список с поиском и чекбоксами
- `LabeledEntry` — поле ввода с меткой
- `LabeledComboBox` — выпадающий список с меткой

#### `gui/main_window.py`
- 3-панельный интерфейс: фильтры / список маршрутов / опции вывода
- Прогресс-бар и лог
- Сохранение/восстановление настроек

---

## Этап 3. Установочные скрипты

### `install.ps1` (Windows)
- Проверка Python 3.10+ и Git
- Клонирование в `%LOCALAPPDATA%\spb-gtfs-gpx\`
- Создание venv, установка зависимостей
- Ярлык на рабочем столе + `.bat` лаунчер
- Проверка Execution Policy с понятным сообщением

### `install.sh` (Linux/macOS)
- Проверка Python 3.10+ и Git
- Клонирование в `~/.local/share/` (Linux) или `~/Library/Application Support/` (Mac)
- Создание venv, установка зависимостей
- `.desktop` файл (Linux) / `.command` файл (Mac)
- Добавление в `PATH`

---

## Этап 4. Публикация на GitHub

1. Инициализация git-репозитория
2. Проверка на отсутствие токенов/паролей в коде и истории git
3. Создание приватного репозитория через GitHub CLI
4. Публикация кода
5. Добавление установочных скриптов
6. Обновление README с инструкциями
7. Перевод в публичный режим (после проверки безопасности)

---

## Этап 5. Исправления багов

### Баг 1: Инвертированные даты в `calendar.txt`
**Симптом:** Только 20 маршрутов вместо ~450  
**Причина:** Все 1005 записей в `calendar.txt` имеют `start_date=20260724, end_date=20191230`. После обмена местами получается `20191230 <= сегодня <= 20260724`, но 27.07.2026 > 24.07.2026  
**Исправление:** При инверсии дат (`start > end`) — игнорировать проверку диапазона, проверять только день недели + `calendar_dates.txt`  
**Результат:** 537 активных service_id вместо 15  
**Файл:** `modules/actuality_checker.py`

### Баг 2: Ошибка NaN при снятии галки «Только действующие»
**Симптом:** Ошибка при экспорте с `only_active=False`  
**Причина:** `int(row.get("num_points", 0))` падает на NaN-значениях (30 строк без geometry)  
**Исправление:** Фильтрация строк без геометрии + безопасное преобразование через `pd.notna()`  
**Файл:** `modules/gui/worker.py`

### Баг 3: Кнопка «Все» сбрасывала выделение
**Симптом:** При поиске выделение чекбоксов сбрасывалось  
**Причина:** `_rebuild_list()` уничтожал все чекбоксы и создавал новые со значением `False`  
**Исправление:** Сохранение множества выбранных `route_id` перед очисткой, восстановление после  
**Файл:** `modules/gui/widgets.py`  
**Примечание:** Позже заменено на `pack`/`pack_forget` (см. Баг 7)

### Баг 4: PowerShell — кодировка
**Симптом:** `В строке отсутствует завершающий символ: "`  
**Причина:** Русские символы и Unicode-стрелка `→` в `install.ps1` ломали парсинг PowerShell на Windows (UTF-8 без BOM)  
**Исправление:** Полный перевод `install.ps1` на английский, удаление спецсимволов  
**Файл:** `install.ps1`

### Баг 5: PowerShell — `Set-Location -`
**Симптом:** `Не удается найти путь "...app\-"`  
**Причина:** `Set-Location -` (возврат к предыдущей директории) не работает в свежей сессии PowerShell  
**Исправление:** Замена на `Push-Location` / `Pop-Location`  
**Файл:** `install.ps1`

### Баг 6: Экспорт — «Нет данных для экспорта»
**Симптом:** При нажатии «Экспорт» — ошибка, хотя маршруты загружены  
**Причина:** `_parser` и `_routes_df` хранились только в worker-потоке, не копировались в главное окно  
**Исправление:** В `_handle_message` при `TYPE_ROUTES_LOADED` — копирование `_parser` и `_routes_df` из worker  
**Дополнительно:** Кнопка «Обновить фид» не передавала `force=True` (стоял TODO) — добавлен параметр `force` в `GTFSWorker`  
**Файлы:** `modules/gui/main_window.py`, `modules/gui/worker.py`

### Баг 7: Лаги при поиске маршрутов
**Симптом:** При вводе текста в поиск — зависание на 2-5 секунд  
**Причина:** Каждое нажатие клавиши → `destroy()` + `create()` ~900 чекбоксов  
**Исправление:**  
1. **Debounce 300мс** — `_on_search` ждёт 300мс после последнего нажатия  
2. **pack/pack_forget** — все чекбоксы создаются один раз при `load_routes()`, фильтрация через `pack_forget()` / `pack()`  
**Результат:** ~50мс вместо 2-5 сек  
**Файл:** `modules/gui/widgets.py`

### Баг 8: Дублирующийся route_id — выбор одного варианта выбирал все
**Симптом:** При выборе одного чекбокса маршрута 176 — выбирался и второй (обратное направление)  
**Причина:** Маршрут 176 имеет 2 варианта (направления) с одинаковым `route_id=1501`. В `_vars` и `_checkboxes` ключом был `route_id` — второй чекбокс перезаписывал первый  
**Исправление:**  
1. Ключом для `_vars` и `_checkboxes` — **индекс** в списке (`"0"`, `"1"`, ...), не `route_id`  
2. Отдельный словарь `_shape_ids` хранит маппинг индекс → `shape_id`  
3. `get_selected_ids()` возвращает `shape_id` (уникальный идентификатор варианта)  
4. `_do_export` фильтрует по `shape_id`, а не по `route_id`  
**Файлы:** `modules/gui/widgets.py`, `modules/gui/worker.py`

### Баг 9: gpxpy API — `lat`/`lon` vs `latitude`/`longitude`
**Симптом:** `TypeError: GPXTrackPoint.__init__() got an unexpected keyword argument 'lat'`  
**Причина:** gpxpy 1.6.2 использует `latitude`/`longitude`, а не `lat`/`lon`  
**Исправление:** Замена `lat=`/`lon=` на `latitude=`/`longitude=`  
**Файл:** `modules/gpx_builder.py`

### Баг 10: Отсутствие `trip_headsign` в trips.txt
**Симптом:** `KeyError: "['trip_headsign'] not in index"`  
**Причина:** В реальном фиде СПб `trips.txt` не содержит колонку `trip_headsign`  
**Исправление:** Проверка наличия колонки перед использованием, fallback на `route_long_name`  
**Файлы:** `modules/gtfs_parser.py`, `modules/gpx_builder.py`

---

## Этап 6. Логика выбора shape-вариантов

### Проблема
Один `route_id` имеет несколько `shape_id` (разные направления, варианты, ветки). При выборе «основного» shape:
- Выбор по `route_id` терял обратное направление
- Мог выбираться неактивный shape

### Решение
1. **Фильтрация на уровне shape_id:** оставляем только shape, используемые активными trip
2. **Группировка по (route_id, direction_id):** сохраняем оба направления
3. **Выбор основного shape:** `sort_values` + `drop_duplicates(subset=["route_id", "direction_id"])`

### Пример
Маршрут №1 (id=1062):
| shape_id | direction | trips | активен | точек |
|---|---|---|---|---|
| track-210021 | 0 (прямой) | 46 | НЕТ | 566 |
| track-210022 | 1 (обратный) | 48 | НЕТ | 540 |
| track-221776 | 0 (прямой) | 55 | да | 566 |
| track-221777 | 1 (обратный) | 55 | да | 540 |

После исправления: только активные shape (221776, 221777), оба направления сохранены.

---

## Настройки приложения

### Фильтры
- Тип транспорта: bus / trolley / tram (по `transport_type`)
- Номера маршрутов: список, диапазоны (`3,7,10-15`)
- Направление: прямое / обратное / оба
- Территория: городские / пригородные / все (по `urban`)
- Ночные маршруты (по `night`)
- Кольцевые (по `circular`)
- Только действующие на дату + выбор даты

### Вариант трека
- Основной (max точек на направление)
- Все варианты
- Длиннейший (по длине на направление)

### Остановки
- Включить/исключить
- Источник: все города / только выбранные маршруты
- Поле имени: stop_name / stop_code / stop_id

### GPX-вывод
- Один общий файл
- Отдельные файлы по маршрутам
- Шаблон имён треков
- Упрощение геометрии (RDP, толерантность в метрах)
- Метаданные GPX

### Сеть/кэш
- URL источника
- Таймаут, прокси, User-Agent
- TTL кэша (часы)
- Принудительное обновление

---

## Сборка

### Windows (.exe)
```bash
pyinstaller build.spec --clean
```

### macOS (.app)
```bash
pyinstaller build.spec --clean
```

### Установка из исходников
```powershell
# Windows
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/whitefoxxy/spb-gtfs-gpx/main/install.ps1" -OutFile "install.ps1"; powershell -ExecutionPolicy Bypass -File ".\install.ps1"
```

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/whitefoxxy/spb-gtfs-gpx/main/install.sh | bash
```
