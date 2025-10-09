"""Application entry point for PhotoWatermarkGUI."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

try:
    from .app import MainWindow
except ImportError:  # pragma: no cover - fallback when executed as script
    package_root = Path(__file__).resolve().parent
    sys.path.insert(0, str(package_root.parent))
    from photowatermark_gui.app import MainWindow


def main() -> None:
    """Launch the PhotoWatermarkGUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("PhotoWatermarkGUI")
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
