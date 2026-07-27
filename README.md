# GTFS → GPX: Маршруты общественного транспорта

GUI-приложение для загрузки GTFS-фидов общественного транспорта и конвертации маршрутов в формат GPX.

## Возможности

- **Автозагрузка GTFS** из интернета с кэшированием и проверкой актуальности
- **Фильтры**: тип транспорта, номера маршрутов, направление, городские/пригородные, ночные, кольцевые
- **Проверка актуальности**: свежесть фида (HTTP Last-Modified) + действующие маршруты по календарю
- **Остановки**: можно включить/исключить, выбрать источник (все / по маршрутам)
- **GPX-вывод**: один общий файл и/или отдельные файлы по маршрутам
- **Упрощение геометрии**: алгоритм Рамера-Дугласа-Пекера
- **Кроссплатформенность**: Windows (.exe), macOS (.app), Linux

## Предустановленный источник

- **Санкт-Петербург** — `transport.orgp.spb.ru`
  - Включает городские и пригородные маршруты (в т.ч. в Ленинградскую область)
  - Поддерживаются автобусы, троллейбусы, трамваи

## Быстрая установка

> **Важно:** репозиторий приватный. Сначала нужно клонировать его через Git (потребуется логин/пароль GitHub или SSH-ключ), затем запустить установочный скрипт локально.

### Windows (PowerShell)

```powershell
# 1. Клонировать репозиторий (введите логин/пароль GitHub при запросе)
git clone https://github.com/whitefoxxy/spb-gtfs-gpx.git

# 2. Запустить установщик
cd spb-gtfs-gpx
.\install.ps1
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
# 1. Клонировать репозиторий (введите логин/пароль GitHub при запросе)
git clone https://github.com/whitefoxxy/spb-gtfs-gpx.git

# 2. Запустить установщик
cd spb-gtfs-gpx
bash install.sh
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
