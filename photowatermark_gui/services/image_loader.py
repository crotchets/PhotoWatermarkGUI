"""Helpers for importing and preparing images."""
from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import Iterable, List

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from .watermark import ALLOWED_INPUT_SUFFIXES


def filter_supported_images(paths: Iterable[Path]) -> List[Path]:
    unique: List[Path] = []
    seen: set[Path] = set()
    queue = deque(Path(p) for p in paths)
    while queue:
        path = queue.popleft()
        try:
            path = path.expanduser().resolve()
        except OSError:
            continue
        if path in seen or not path.exists():
            continue
        if path.is_dir():
            for child in path.iterdir():
                queue.append(child)
            seen.add(path)
            continue
        suffix = path.suffix.lower()
        if suffix in ALLOWED_INPUT_SUFFIXES:
            unique.append(path)
            seen.add(path)
    return unique


def load_qimage(path: Path) -> QImage:
    image = QImage(str(path))
    return image


def make_thumbnail(path: Path, size: int = 96) -> QPixmap:
    image = QImage(str(path))
    if image.isNull():
        return QPixmap()
    scaled = image.scaled(size, size, transformMode=Qt.TransformationMode.SmoothTransformation, aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio)
    pixmap = QPixmap.fromImage(scaled)
    return pixmap
