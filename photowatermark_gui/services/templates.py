"""Template persistence layer."""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ExportSettings, WatermarkSettings

APP_DIR = Path.home() / ".photo_watermark_gui"
TEMPLATES_FILE = APP_DIR / "templates.json"
LAST_SESSION_FILE = APP_DIR / "last_session.json"


class TemplateManager:
    """Handles saving and loading watermark templates."""

    def __init__(self) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> List[str]:
        payload = self._read_file(TEMPLATES_FILE)
        return sorted(payload.keys()) if payload else []

    def load_template(self, name: str) -> Optional[Dict]:
        payload = self._read_file(TEMPLATES_FILE)
        if not payload:
            return None
        return payload.get(name)

    def save_template(
        self,
        name: str,
        watermark: WatermarkSettings,
        export: ExportSettings,
    ) -> None:
        payload = self._read_file(TEMPLATES_FILE) or {}
        payload[name] = {
            "watermark": watermark.to_dict(),
            "export": export.to_dict(),
        }
        self._write_file(TEMPLATES_FILE, payload)

    def delete_template(self, name: str) -> None:
        payload = self._read_file(TEMPLATES_FILE) or {}
        if name in payload:
            payload.pop(name)
            self._write_file(TEMPLATES_FILE, payload)

    def rename_template(self, old_name: str, new_name: str) -> bool:
        if old_name == new_name:
            return True
        payload = self._read_file(TEMPLATES_FILE) or {}
        if old_name not in payload:
            return False
        if new_name in payload:
            return False
        payload[new_name] = payload.pop(old_name)
        self._write_file(TEMPLATES_FILE, payload)
        return True

    def save_last_session(self, data: Dict) -> None:
        self._write_file(LAST_SESSION_FILE, data)

    def load_last_session(self) -> Optional[Dict]:
        return self._read_file(LAST_SESSION_FILE)

    def has_last_session(self) -> bool:
        return LAST_SESSION_FILE.exists()

    def _read_file(self, path: Path) -> Optional[Dict]:
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError:
            return None

    def _write_file(self, path: Path, data: Dict) -> None:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
