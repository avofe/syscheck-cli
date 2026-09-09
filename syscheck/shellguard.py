"""Безопасность !shell.

!shell по умолчанию ВЫКЛЮЧЕН. Включается только явным флагом --enable-shell.
При первом включении требуется подтверждение, результат сохраняется в
конфиг-файл. Каждая выполненная команда логируется в audit-лог.

Логика вынесена в отдельный модуль, чтобы её было легко тестировать
и переиспользовать из TUI и CLI.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

# Директория конфига (например ~/.syscheck)
CONFIG_DIR = Path(os.environ.get("SYSSCHECK_CONFIG_DIR", "~/.syscheck")).expanduser()
CONFIG_FILE = CONFIG_DIR / "config.json"
AUDIT_LOG = CONFIG_DIR / "shell_audit.log"

# Текст предупреждения при первом включении
WARNING_TEXT = (
    "!shell выполняет ЛЮБЫЕ команды операционной системы с твоими правами.\n"
    "Используй только если доверяешь тому, кто дал тебе этот инструмент.\n"
    "Каждое выполнение будет записано в лог: {audit}"
)


class ShellDisabledError(RuntimeError):
    """Возникает при вызове !shell, пока функция отключена."""


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def is_enabled() -> bool:
    """Читает конфиг: включён ли !shell."""
    try:
        if not CONFIG_FILE.exists():
            return False
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return bool(data.get("shell_enabled", False))
    except (json.JSONDecodeError, OSError):
        return False


def set_enabled(enabled: bool) -> None:
    """Сохраняет состояние !shell в конфиг."""
    _ensure_dir()
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data["shell_enabled"] = enabled
    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def needs_first_confirmation() -> bool:
    """Нужно ли показать предупреждение при первом включении."""
    try:
        if not CONFIG_FILE.exists():
            return True
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        # метка, что пользователь уже видел предупреждение
        return not bool(data.get("shell_warned", False))
    except (json.JSONDecodeError, OSError):
        return True


def mark_warned() -> None:
    """Помечает, что предупреждение было показано."""
    _ensure_dir()
    data = {}
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    data["shell_warned"] = True
    CONFIG_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def log_command(cmd: str) -> None:
    """Пишет выполненную команду в audit-лог."""
    _ensure_dir()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {cmd}\n")


def run_shell(cmd: str, timeout: int = 30) -> str:
    """Выполняет команду, если !shell включён. Иначе бросает ShellDisabledError."""
    if not is_enabled():
        raise ShellDisabledError(
            "!shell отключён. Запусти syscheck с флагом --enable-shell, "
            "чтобы включить выполнение системных команд."
        )
    log_command(cmd)
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout or result.stderr
        return out if out else f"(no output, exit code {result.returncode})"
    except subprocess.TimeoutExpired:
        return "команда превысила таймаут (30 с)"
    except Exception as e:
        return f"ошибка: {e}"


def resolve_confirmation(cmd: str) -> str:
    """Формирует текст запроса на подтверждение (требуется на КАЖДУЮ команду)."""
    return (
        f"команда: {cmd}\n"
        "наберите её ещё раз или 'confirm', чтобы выполнить, "
        "или что угодно для отмены"
    )
