from __future__ import annotations

from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
import sys
from typing import Any, TypeVar, get_type_hints

from trading_bot.config.models import Settings

T = TypeVar("T")


def load_settings(path: str | Path | None = None) -> Settings:
    settings = Settings()
    default_path = _resolve_config_path("configs/default.yaml")
    if path is None:
        if default_path.exists():
            return _apply_dataclass(settings, _load_yaml_like(default_path))
        return settings
    config_path = _resolve_config_path(path)
    if default_path.exists() and config_path.resolve() != default_path.resolve():
        settings = _apply_dataclass(settings, _load_yaml_like(default_path))
    raw = _load_yaml_like(config_path)
    return _apply_dataclass(settings, raw)


def _resolve_config_path(path: str | Path) -> Path:
    requested = Path(path)
    if requested.is_absolute() or requested.exists():
        return requested
    for root in _runtime_roots():
        candidate = root / requested
        if candidate.exists():
            return candidate
    return requested


def _runtime_roots() -> list[Path]:
    roots = [Path.cwd()]
    if getattr(sys, "frozen", False):
        roots.append(Path(sys.executable).resolve().parent)
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(bundle_root))
    return roots


def _load_yaml_like(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        loaded = yaml.safe_load(text) or {}
        if not isinstance(loaded, dict):
            return {}
        return loaded
    except ModuleNotFoundError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, sep, raw_value = line.strip().partition(":")
        if not sep:
            continue
        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        if raw_value.strip() == "":
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent, child))
        else:
            current[key] = _coerce_scalar(raw_value.strip())
    return root


def _coerce_scalar(value: str) -> Any:
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    try:
        if "." in value:
            return Decimal(value)
        return int(value)
    except Exception:
        return value.strip("\"'")


def _apply_dataclass(instance: T, raw: dict[str, Any]) -> T:
    if not is_dataclass(instance):
        return instance
    hints = get_type_hints(type(instance))
    for item in fields(instance):
        if item.name not in raw:
            continue
        value = raw[item.name]
        current = getattr(instance, item.name)
        if is_dataclass(current) and isinstance(value, dict):
            setattr(instance, item.name, _apply_dataclass(current, value))
        else:
            setattr(instance, item.name, _coerce_to_type(value, hints.get(item.name, item.type)))
    return instance


def _coerce_to_type(value: Any, target: Any) -> Any:
    if target is Decimal:
        return Decimal(str(value))
    if target is int:
        return int(value)
    if target is bool:
        if isinstance(value, bool):
            return value
        return str(value).lower() == "true"
    if target is str:
        return str(value)
    return value
