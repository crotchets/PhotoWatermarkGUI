"""Watermark rendering helpers."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from PIL import Image, ImageDraw, ImageFont

from ..models import ExportSettings, WatermarkSettings

ALLOWED_INPUT_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
DEFAULT_FONT_FALLBACKS = [
    # Windows
    Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "arial.ttf",
    # macOS
    Path("/Library/Fonts/Arial.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    # Linux common fallback
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]


def locate_default_font() -> Path:
    for candidate in DEFAULT_FONT_FALLBACKS:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No default font file found. Please install Arial or DejaVuSans.")


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


def render_text_watermark(
    base_size: Tuple[int, int],
    watermark: WatermarkSettings,
    font_path: Path | None = None,
) -> Image.Image:
    width, height = base_size
    canvas = Image.new("RGBA", base_size, (0, 0, 0, 0))
    drawer = ImageDraw.Draw(canvas)
    font_file = font_path or locate_default_font()
    try:
        font = ImageFont.truetype(str(font_file), watermark.font_size)
    except OSError:
        font = ImageFont.load_default()

    text_lines = watermark.text.splitlines() or [""]
    line_heights = []
    line_widths = []
    for line in text_lines:
        bbox = drawer.textbbox((0, 0), line if line else " ", font=font)
        line_widths.append(bbox[2] - bbox[0])
        line_heights.append(bbox[3] - bbox[1])

    text_width = max(line_widths)
    text_height = sum(line_heights)

    # compute top-left via ratio (0-1) relative to remaining space
    available_w = max(width - text_width, 1)
    available_h = max(height - text_height, 1)
    x = watermark.position_ratio.x() * available_w
    y = watermark.position_ratio.y() * available_h
    alpha = int(255 * (watermark.opacity / 100))

    current_y = y
    for line, line_height in zip(text_lines, line_heights):
        drawer.text((x, current_y), line, font=font, fill=(255, 255, 255, alpha))
        current_y += line_height

    if watermark.rotation:
        canvas = canvas.rotate(-watermark.rotation, expand=1, center=(width / 2, height / 2))
    return canvas


def compose_watermark(
    image: Image.Image,
    watermark_settings: WatermarkSettings,
) -> Image.Image:
    watermark_layer = render_text_watermark(image.size, watermark_settings)
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
