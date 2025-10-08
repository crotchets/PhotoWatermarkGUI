"""Data models for PhotoWatermarkGUI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import QPointF


@dataclass
class WatermarkSettings:
    """Watermark configuration parameters."""

    text: str = "Sample Watermark"
    opacity: int = 70  # 0-100
    font_size: int = 36
    font_family: str = "Arial"
    bold: bool = False
    italic: bool = False
    color: str = "#FFFFFF"
    shadow: bool = False
    outline: bool = False
    position_ratio: QPointF = field(default_factory=lambda: QPointF(0.5, 0.5))
    rotation: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "opacity": self.opacity,
            "font_size": self.font_size,
            "font_family": self.font_family,
            "bold": self.bold,
            "italic": self.italic,
            "color": self.color,
            "shadow": self.shadow,
            "outline": self.outline,
            "rotation": self.rotation,
            "position_ratio": {
                "x": self.position_ratio.x(),
                "y": self.position_ratio.y(),
            },
        }

    @classmethod
    def from_dict(cls, raw: Dict | None) -> "WatermarkSettings":
        if not raw:
            return cls()
        ratio = raw.get("position_ratio", {})
        return cls(
            text=raw.get("text", "Sample Watermark"),
            opacity=int(raw.get("opacity", 70)),
            font_size=int(raw.get("font_size", 36)),
            font_family=raw.get("font_family", "Arial"),
            bold=bool(raw.get("bold", False)),
            italic=bool(raw.get("italic", False)),
            color=raw.get("color", "#FFFFFF"),
            shadow=bool(raw.get("shadow", False)),
            outline=bool(raw.get("outline", False)),
            rotation=float(raw.get("rotation", 0.0)),
            position_ratio=QPointF(
                float(ratio.get("x", 0.5)),
                float(ratio.get("y", 0.5)),
            ),
        )


@dataclass
class ExportSettings:
    """Batch export options."""

    output_dir: Optional[Path] = None
    output_format: str = "auto"  # auto, jpeg, png
    naming_mode: str = "original"  # original, prefix, suffix
    prefix: str = "wm_"
    suffix: str = "_watermarked"
    jpeg_quality: int = 95
    scale_mode: str = "none"  # none, width, height, percent
    scale_value: int = 100

    def to_dict(self) -> Dict:
        return {
            "output_dir": str(self.output_dir) if self.output_dir else None,
            "output_format": self.output_format,
            "naming_mode": self.naming_mode,
            "prefix": self.prefix,
            "suffix": self.suffix,
            "jpeg_quality": self.jpeg_quality,
            "scale_mode": self.scale_mode,
            "scale_value": self.scale_value,
        }

    @classmethod
    def from_dict(cls, raw: Dict | None) -> "ExportSettings":
        if not raw:
            return cls()
        path = raw.get("output_dir")
        return cls(
            output_dir=Path(path) if path else None,
            output_format=raw.get("output_format", "auto"),
            naming_mode=raw.get("naming_mode", "original"),
            prefix=raw.get("prefix", "wm_"),
            suffix=raw.get("suffix", "_watermarked"),
            jpeg_quality=int(raw.get("jpeg_quality", 95)),
            scale_mode=raw.get("scale_mode", "none"),
            scale_value=int(raw.get("scale_value", 100)),
        )
