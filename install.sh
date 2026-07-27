#!/usr/bin/env bash
# =============================================================================
# Установщик GTFS → GPX конвертера для Linux / macOS
# =============================================================================
set -euo pipefail

REPO_URL="https://github.com/whitefoxxy/spb-gtfs-gpx.git"
APP_NAME="spb-gtfs-gpx"

# Определяем OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     INSTALL_DIR="$HOME/.local/share/$APP_NAME" ;;
    Darwin*)    INSTALL_DIR="$HOME/Library/Application Support/$APP_NAME" ;;
    *)          INSTALL_DIR="$HOME/.$APP_NAME" ;;
esac

REPO_DIR="$INSTALL_DIR/app"
VENV_DIR="$INSTALL_DIR/venv"
LAUNCHER_DIR="$INSTALL_DIR"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

step() { echo -e "${CYAN}[+]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
err()  { echo -e "${RED}[ERR]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }

# --- 1. Проверка Python ---
step "Проверка Python..."
if ! command -v python3 &> /dev/null; then
    err "Python 3 не найден. Установите Python 3.10+:"
    echo "  Linux: sudo apt install python3 python3-venv python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

PY_VER=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    err "Требуется Python 3.10+. Установлен: $PY_VER"
    exit 1
fi
ok "Python $PY_VER"

# --- 2. Проверка Git ---
step "Проверка Git..."
if ! command -v git &> /dev/null; then
    err "Git не найден. Установите:"
    echo "  Linux: sudo apt install git"
    echo "  macOS: brew install git"
    exit 1
fi
ok "$(git --version)"

# --- 3. Создание директории ---
step "Создание директории установки: $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

# --- 4. Клонирование репозитория ---
if [ -d "$REPO_DIR/.git" ]; then
    step "Репозиторий уже существует. Обновление..."
    git -C "$REPO_DIR" pull
else
    step "Клонирование репозитория..."
    git clone "$REPO_URL" "$REPO_DIR"
fi
ok "Репозиторий готов"

# --- 5. Создание виртуального окружения ---
step "Создание виртуального окружения..."
if [ -d "$VENV_DIR" ]; then
    rm -rf "$VENV_DIR"
fi
python3 -m venv "$VENV_DIR"
ok "Venv создан"

# --- 6. Установка зависимостей ---
step "Установка зависимостей..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"
ok "Зависимости установлены"

# --- 7. Создание лаунчера ---
LAUNCHER_PATH="$LAUNCHER_DIR/$APP_NAME"
cat > "$LAUNCHER_PATH" << 'EOF'
#!/usr/bin/env bash
# GTFS → GPX Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
cd "$SCRIPT_DIR/app"
python main.py
EOF
chmod +x "$LAUNCHER_PATH"
ok "Лаунчер создан: $LAUNCHER_PATH"

# --- 8. Создание .desktop файла (Linux) ---
if [ "$OS" = "Linux" ]; then
    step "Создание .desktop файла..."
    DESKTOP_DIR="${XDG_DESKTOP_DIR:-$HOME/Desktop}"
    mkdir -p "$DESKTOP_DIR"
    DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=GTFS → GPX
Comment=Конвертер маршрутов общественного транспорта
Exec=$LAUNCHER_PATH
Icon=applications-internet
Type=Application
Terminal=false
Categories=Utility;Geography;
EOF
    chmod +x "$DESKTOP_FILE"
    ok "Ярлык на рабочем столе: $DESKTOP_FILE"

    # Добавляем в PATH через ~/.local/bin
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
    if [ ! -L "$BIN_DIR/$APP_NAME" ]; then
        ln -s "$LAUNCHER_PATH" "$BIN_DIR/$APP_NAME" 2>/dev/null || true
        ok "Ссылка в PATH: $BIN_DIR/$APP_NAME"
    fi
fi

# --- 9. Создание .command файла (macOS) ---
if [ "$OS" = "Darwin" ]; then
    step "Создание .command файла для macOS..."
    DESKTOP_DIR="$HOME/Desktop"
    COMMAND_FILE="$DESKTOP_DIR/$APP_NAME.command"
    cat > "$COMMAND_FILE" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR"
source "$VENV_DIR/bin/activate"
cd "$REPO_DIR"
python main.py
EOF
    chmod +x "$COMMAND_FILE"
    ok "Ярлык на рабочем столе: $COMMAND_FILE"

    # Добавляем в PATH через /usr/local/bin
    if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
        if [ ! -L "/usr/local/bin/$APP_NAME" ]; then
            ln -s "$LAUNCHER_PATH" "/usr/local/bin/$APP_NAME" 2>/dev/null || true
            ok "Ссылка в PATH: /usr/local/bin/$APP_NAME"
        fi
    fi
fi

# --- Готово ---
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Установка завершена!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Запуск:"
if [ "$OS" = "Linux" ]; then
    echo "  - Двойной клик по ярлыку на рабочем столе"
    echo "  - Или: $LAUNCHER_PATH"
    echo "  - Или в терминале: $APP_NAME"
elif [ "$OS" = "Darwin" ]; then
    echo "  - Двойной клик по .command на рабочем столе"
    echo "  - Или: $LAUNCHER_PATH"
    echo "  - Или в терминале: $APP_NAME"
fi
echo ""
echo "Удаление: rm -rf $INSTALL_DIR"
echo ""

# Предложение запустить
read -rp "Запустить сейчас? (y/n) " run_now
if [ "$run_now" = "y" ] || [ "$run_now" = "Y" ]; then
    "$VENV_DIR/bin/python" "$REPO_DIR/main.py"
fi
