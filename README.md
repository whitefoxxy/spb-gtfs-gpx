# GTFS → GPX: Маршруты общественного транспорта

GUI-приложение для загрузки GTFS-фидов общественного транспорта и конвертации маршрутов в формат GPX.

## Возможности

- **Автозагрузка GTFS** из интернета с кэшированием и проверкой актуальности
- **Фильтры**: тип транспорта, номера маршрутов, направление, городские/пригородные, ночные, кольцевые
- **Проверка актуальности**: свежесть фида (HTTP Last-Modified) + действующие маршруты по календарю
- **Сортировка маршрутов** по номеру (числовая, с учётом буквенных суффиксов)
- **Объединение маршрутов** в один трек без дублирования общих участков дорог
- **Применение фильтра без перезагрузки** — мгновенное перефильтрование загруженных данных
- **Остановки**: можно включить/исключить, выбрать источник (все / по маршрутам)
- **GPX-вывод**: один общий файл и/или отдельные файлы по маршрутам
- **Упрощение геометрии**: алгоритм Рамера-Дугласа-Пекера
- **Кроссплатформенность**: Windows (.exe), macOS (.app), Linux

## Предустановленный источник

- **Санкт-Петербург** — `transport.orgp.spb.ru`
  - Включает городские и пригородные маршруты (в т.ч. в Ленинградскую область)
  - Поддерживаются автобусы, троллейбусы, трамваи

## Быстрая установка

### Windows (PowerShell)

> **Важно:** PowerShell по умолчанию блокирует выполнение скриптов. Используйте команду с обходом политики:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/whitefoxxy/spb-gtfs-gpx/main/install.ps1" -OutFile "install.ps1"; powershell -ExecutionPolicy Bypass -File ".\install.ps1"
```

**Что делает:**
- Проверяет Python 3.10+ и Git
- Клонирует репозиторий в `%LOCALAPPDATA%\spb-gtfs-gpx\`
- Создаёт виртуальное окружение и устанавливает зависимости
- Создаёт ярлык на рабочем столе

**Запуск:** двойной клик по ярлыку на рабочем столе

**Удаление:** `Remove-Item -Recurse -Force "$env:LOCALAPPDATA\spb-gtfs-gpx"`

### Linux / macOS (Bash)

```bash
curl -fsSL https://raw.githubusercontent.com/whitefoxxy/spb-gtfs-gpx/main/install.sh | bash
```

**Что делает:**
- Проверяет Python 3.10+ и Git
- Клонирует репозиторий (`~/.local/share/` на Linux, `~/Library/Application Support/` на macOS)
- Создаёт виртуальное окружение и устанавливает зависимости
- Создаёт ярлык на рабочем столе и добавляет в `PATH`

**Запуск:**
- **Linux:** двойной клик по ярлыку или команда `spb-gtfs-gpx` в терминале
- **macOS:** двойной клик по `.command` файлу или команда `spb-gtfs-gpx` в терминале

**Удаление:**
```bash
rm -rf ~/.local/share/spb-gtfs-gpx        # Linux
rm -rf ~/Library/Application\ Support/spb-gtfs-gpx  # macOS
```

## Ручная установка (для разработчиков)

### Установка зависимостей

```bash
pip install -r requirements.txt
```

## Запуск

```bash
python main.py
```

## Сборка исполняемого файла

### Windows (.exe)

```bash
pyinstaller build.spec --clean
```

Результат: `dist/spb-gtfs-gpx.exe`

### macOS (.app)

```bash
pyinstaller build.spec --clean
```

Результат: `dist/spb-gtfs-gpx.app`

## Структура проекта

```
spb_gtfs_gpx/
├── main.py                  # Точка входа
├── build.spec               # PyInstaller spec
├── requirements.txt         # Зависимости
├── install.ps1              # Установщик Windows
├── install.sh               # Установщик Linux/macOS
├── modules/
│   ├── paths.py             # Кроссплатформенные пути
│   ├── settings.py          # Настройки + config.json
│   ├── gtfs_downloader.py   # Загрузка + кэш
│   ├── gtfs_parser.py       # Парсинг CSV
│   ├── actuality_checker.py # Проверка актуальности
│   ├── gpx_builder.py       # Генерация GPX
│   └── gui/
│       ├── main_window.py   # Главное окно
│       ├── widgets.py       # Виджеты
│       └── worker.py        # Фоновый поток
```

## Настройки

Сохраняются автоматически в `config.json` (платформозависимый путь):
- Windows: `%APPDATA%/spb-gtfs-gpx/config.json`
- macOS: `~/Library/Application Support/spb-gtfs-gpx/config.json`
- Linux: `~/.config/spb-gtfs-gpx/config.json`

## Кэш GTFS

ZIP-файлы фидов кэшируются в платформозависимой директории:
- Windows: `%LOCALAPPDATA%/spb-gtfs-gpx/cache/feeds/`
- macOS: `~/Library/Caches/spb-gtfs-gpx/feeds/`
- Linux: `~/.cache/spb-gtfs-gpx/feeds/`

По умолчанию TTL = 24 часа. При устаревании кэша выполняется условный GET (If-Modified-Since).
