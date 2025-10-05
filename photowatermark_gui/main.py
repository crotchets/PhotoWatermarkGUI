"""Application entry point for PhotoWatermarkGUI."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from .app import MainWindow


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
