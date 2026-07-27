"""Точка входа в приложение GTFS → GPX."""
import sys

# Для PyInstaller: добавляем путь к модулям
if getattr(sys, "frozen", False):
    import os
    sys.path.insert(0, os.path.dirname(sys.executable))

from modules.gui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
