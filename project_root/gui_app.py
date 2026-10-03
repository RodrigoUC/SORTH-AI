# gui_app.py

"""
SORTH - Sistema de Organización de Horarios
Interfaz gráfica principal

Para ejecutar:
    python gui_app.py
"""

import sys
from pathlib import Path
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow


def _resolve_icon_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "sorth.ico"
    return Path(__file__).parent / "assets" / "sorth.ico"


def _set_windows_app_id() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SORTH.App")
    except Exception:
        pass


def main():
    if "--recover-session" in sys.argv:
        from src.application.recovery_command import run
        sys.exit(run(sys.argv[1:]))
    _set_windows_app_id()
    app = QApplication(sys.argv)
    app.setApplicationName("SORTH")
    app.setOrganizationName("SORTH")

    icon_path = _resolve_icon_path()
    icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    if "--smoke-test" in sys.argv:
        import argparse
        from src.application.packaged_smoke import run_smoke_test
        parser = argparse.ArgumentParser(description="Validate SORTH in an isolated session")
        parser.add_argument("--smoke-test", action="store_true")
        parser.add_argument("--smoke-output", type=Path, required=True)
        args = parser.parse_args()
        sys.exit(run_smoke_test(app, args.smoke_output))

    window = MainWindow()
    if not icon.isNull():
        window.setWindowIcon(icon)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
