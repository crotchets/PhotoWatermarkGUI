"""Watermark rendering helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageQt

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen
from PyQt6.QtGui import QImage as QtImage

from ..models import ExportSettings, WatermarkSettings

ALLOWED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def scale_image(image: Image.Image, settings: ExportSettings) -> Image.Image:
    if settings.scale_mode == "none":
        return image
    width, height = image.size
    if settings.scale_mode == "percent":
        ratio = settings.scale_value / 100.0
        return image.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)
    if settings.scale_mode == "width" and settings.scale_value > 0:
        new_width = settings.scale_value
        ratio = new_width / width
        return image.resize((new_width, int(height * ratio)), Image.Resampling.LANCZOS)
    if settings.scale_mode == "height" and settings.scale_value > 0:
        new_height = settings.scale_value
        ratio = new_height / height
        return image.resize((int(width * ratio), new_height), Image.Resampling.LANCZOS)
    return image


def _build_text_path(text: str, font: QFont) -> QPainterPath:
    metrics = QFontMetrics(font)
    lines = text.splitlines() or [""]
    path = QPainterPath()
    y = 0
    for line in lines:
        content = line or " "
        path.addText(0, y + metrics.ascent(), font, content)
        y += metrics.lineSpacing()
    if path.isEmpty():
        path.addText(0, metrics.ascent(), font, " ")
    rect = path.boundingRect()
    if rect.x() != 0 or rect.y() != 0:
        path.translate(-rect.x(), -rect.y())
    return path


def _parse_color(color: str, alpha: int) -> QColor:
    qcolor = QColor(color if color else "#FFFFFF")
    qcolor.setAlpha(alpha)
    return qcolor


def _render_text_layer(
    base_size: Tuple[int, int],
    watermark: WatermarkSettings,
) -> Image.Image:
    width, height = base_size
    if width <= 0 or height <= 0:
        return Image.new("RGBA", base_size, (0, 0, 0, 0))

    image = QtImage(width, height, QtImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.TextAntialiasing
        | QPainter.RenderHint.SmoothPixmapTransform
    )

    font = QFont(watermark.font_family or "Arial", pointSize=watermark.font_size)
    font.setBold(watermark.bold)
    font.setItalic(watermark.italic)
    path = _build_text_path(watermark.text, font)
    rect = path.boundingRect()

    available_w = max(width - rect.width(), 1)
    available_h = max(height - rect.height(), 1)
    pos_x = watermark.position_ratio.x() * available_w
    pos_y = watermark.position_ratio.y() * available_h

    translate_x = pos_x
    translate_y = pos_y

    alpha = int(255 * (watermark.opacity / 100))
    fill_color = _parse_color(watermark.color, alpha)
    shadow_offset = max(2.0, font.pointSizeF() * 0.08)
    outline_width = max(1.5, font.pointSizeF() * 0.1)

    painter.translate(translate_x, translate_y)
    if watermark.rotation:
        center = rect.center()
        painter.translate(center)
        painter.rotate(-watermark.rotation)
        painter.translate(-center)

    if watermark.shadow:
        shadow_color = QColor(0, 0, 0, int(alpha * 0.6))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shadow_color)
        painter.drawPath(path.translated(shadow_offset, shadow_offset))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(fill_color)
    painter.drawPath(path)

    if watermark.outline:
        outline_color = QColor(0, 0, 0, alpha)
        pen = QPen(outline_color, outline_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    painter.end()

    pil_image = ImageQt.fromqimage(image)
    return pil_image.copy()


def _apply_opacity(pil_image: Image.Image, opacity: int) -> Image.Image:
    if pil_image.mode != "RGBA":
        pil_image = pil_image.convert("RGBA")
    if opacity >= 100:
        return pil_image
    alpha = pil_image.split()[-1]
    factor = max(0.0, min(1.0, opacity / 100.0))

    def scale(value: int) -> int:
        return int(value * factor)

    alpha = alpha.point(scale)
    pil_image.putalpha(alpha)
    return pil_image


def _render_image_layer(
    base_size: Tuple[int, int],
    watermark: WatermarkSettings,
) -> Image.Image:
    width, height = base_size
    if width <= 0 or height <= 0 or not watermark.image_path:
        return Image.new("RGBA", base_size, (0, 0, 0, 0))

    image_path = Path(watermark.image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"水印图片未找到：{image_path}")

    overlay = Image.open(image_path).convert("RGBA")
    scale_percent = max(1, watermark.image_scale)
    scale_factor = scale_percent / 100.0
    new_size = (
        max(1, int(overlay.width * scale_factor)),
        max(1, int(overlay.height * scale_factor)),
    )
    overlay = overlay.resize(new_size, Image.Resampling.LANCZOS)
    overlay = _apply_opacity(overlay, watermark.opacity)

    if watermark.rotation:
        overlay = overlay.rotate(-watermark.rotation, expand=True, resample=Image.Resampling.BICUBIC)

    layer = Image.new("RGBA", base_size, (0, 0, 0, 0))
    available_w = max(width - overlay.width, 1)
    available_h = max(height - overlay.height, 1)
    pos_x = int(watermark.position_ratio.x() * available_w)
    pos_y = int(watermark.position_ratio.y() * available_h)

    layer.paste(overlay, (pos_x, pos_y), mask=overlay)
    return layer


def render_watermark_layer(
    base_size: Tuple[int, int],
    watermark: WatermarkSettings,
) -> Image.Image:
    if watermark.mode == "image":
        return _render_image_layer(base_size, watermark)
    return _render_text_layer(base_size, watermark)


def compose_watermark(
    image: Image.Image,
    watermark_settings: WatermarkSettings,
) -> Image.Image:
    watermark_layer = render_watermark_layer(image.size, watermark_settings)
    return Image.alpha_composite(image.convert("RGBA"), watermark_layer)


def compute_output_path(
    source: Path,
    export: ExportSettings,
    output_dir: Path,
) -> Path:
    stem = source.stem
    if export.naming_mode == "prefix":
        stem = f"{export.prefix}{stem}"
    elif export.naming_mode == "suffix":
        stem = f"{stem}{export.suffix}"

    if export.output_format == "jpeg":
        suffix = ".jpg"
    elif export.output_format == "png":
        suffix = ".png"
    else:
        suffix = source.suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            suffix = ".png"
    return output_dir / f"{stem}{suffix}"
