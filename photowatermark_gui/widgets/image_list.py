"""Image list widget with drag-and-drop support."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from ..services.image_loader import filter_supported_images, make_thumbnail


class ImageListWidget(QListWidget):
    """Displays imported images with thumbnails."""

    def __init__(self, on_paths_added: Callable[[List[Path]], None], parent=None) -> None:
        super().__init__(parent)
        self._on_paths_added = on_paths_added
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        urls = event.mimeData().urls()
        paths = [Path(u.toLocalFile()) for u in urls if u.isLocalFile()]
        filtered = filter_supported_images(paths)
        if filtered:
            self._on_paths_added(filtered)
            event.acceptProposedAction()
        else:
            event.ignore()

    def populate(self, paths: Iterable[Path], selected: Path | None = None) -> None:
        self.clear()
        selected_row = -1
        for index, path in enumerate(paths):
            item = QListWidgetItem(path.name)
            pixmap = make_thumbnail(path)
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.addItem(item)
            if selected and path == selected:
                selected_row = index
        if selected_row >= 0:
            self.setCurrentRow(selected_row)
