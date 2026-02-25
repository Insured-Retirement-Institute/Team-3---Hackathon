"""Store and load carrier request/response format YAML per carrier (local_data/carrier_formats/)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _formats_dir() -> Path:
    d = _backend_dir() / "local_data" / "carrier_formats"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _format_path(carrier_id: str) -> Path:
    # Normalize to a safe filename
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in carrier_id.strip())
    if not safe:
        safe = "default"
    return _formats_dir() / f"{safe}.yaml"


def save_carrier_format(carrier_id: str, yaml_content: str) -> str:
    path = _format_path(carrier_id)
    path.write_text(yaml_content, encoding="utf-8")
    return str(path.relative_to(_backend_dir()))


def load_carrier_format(carrier_id: str) -> Optional[str]:
    path = _format_path(carrier_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def list_carrier_format_ids() -> list[str]:
    d = _formats_dir()
    if not d.exists():
        return []
    return [p.stem for p in d.glob("*.yaml")]
