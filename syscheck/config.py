"""Конфигурация syscheck: TOML-файл + значения по умолчанию.

Файл: {SYSCHECK_CONFIG_DIR}/config.toml (по умолчанию ~/.syscheck/config.toml).

Все пороги/интервалы живут в одном месте, чтобы CLI, TUI и палитра
красок опирались на одни и те же числа.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib  # type: ignore

CONFIG_DIR = Path(os.environ.get("SYSCHECK_CONFIG_DIR", "~/.syscheck")).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULTS: Dict[str, Any] = {
    "refresh_interval": 2.0,
    "watch_interval": 2,
    "ping_host": "8.8.8.8",
    "default_panels": ["cpu", "ram", "disk", "net", "procs"],
    "thresholds": {
        "cpu": {"warn": 75, "crit": 90},
        "mem": {"warn": 85, "crit": 90},
        "disk": {"warn": 85, "crit": 95},
    },
}

_loaded: Optional[Dict[str, Any]] = None


def _merge(base: Dict[str, Any], over: Dict[str, Any]) -> Dict[str, Any]:
    """Глубокое слияние словарей: over перекрывает base."""
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _validate(data: Dict[str, Any]) -> None:
    """Нормализует числа: интервал > 0, warn < crit, панели — список."""
    try:
        interval = float(data.get("refresh_interval") or DEFAULTS["refresh_interval"])
        data["refresh_interval"] = max(interval, 0.1)
    except (TypeError, ValueError):
        data["refresh_interval"] = DEFAULTS["refresh_interval"]
    try:
        watch = int(data.get("watch_interval") or DEFAULTS["watch_interval"])
        data["watch_interval"] = max(watch, 1)
    except (TypeError, ValueError):
        data["watch_interval"] = DEFAULTS["watch_interval"]
    panels = data.get("default_panels") or DEFAULTS["default_panels"]
    if not isinstance(panels, list) or not all(isinstance(p, str) for p in panels):
        panels = DEFAULTS["default_panels"]
    data["default_panels"] = panels
    th = data.get("thresholds") or {}
    for name, default in DEFAULTS["thresholds"].items():
        t = th.get(name) or {}
        try:
            warn = float(t.get("warn") or default["warn"])
            crit = float(t.get("crit") or default["crit"])
        except (TypeError, ValueError):
            warn, crit = default["warn"], default["crit"]
        if crit < warn:
            warn, crit = crit, warn
        th[name] = {"warn": warn, "crit": crit}
    data["thresholds"] = th


def load() -> Dict[str, Any]:
    """Читает конфиг один раз (кэш). Битый файл не роняет приложение."""
    global _loaded
    if _loaded is not None:
        return _loaded
    data = _merge(DEFAULTS, {})
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "rb") as f:
                user = tomllib.load(f)
            data = _merge(data, user)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        data["_error"] = str(exc)
    _validate(data)
    _loaded = data
    return data


def reload() -> None:
    """Сбрасывает кэш (для тестов и перечитывания)."""
    global _loaded
    _loaded = None


def get(key: str, default: Any = None) -> Any:
    return load().get(key, default)


def refresh_interval() -> float:
    return float(get("refresh_interval") or DEFAULTS["refresh_interval"])


def watch_interval() -> int:
    return int(get("watch_interval") or DEFAULTS["watch_interval"])


def ping_host() -> str:
    return str(get("ping_host") or DEFAULTS["ping_host"])


def default_panels() -> list:
    return list(get("default_panels") or DEFAULTS["default_panels"])


def thresholds(name: str = "cpu") -> Tuple[float, float]:
    """Пороги (warn, crit) для категории cpu/mem/disk."""
    t = (get("thresholds") or {}).get(name) or DEFAULTS["thresholds"].get(name, {})
    return float(t.get("warn")), float(t.get("crit"))