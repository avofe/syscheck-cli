"""Командный язык syscheck.

Грамматика разделена на группы:

    Info       cpu, ram, gpu, disk, battery, temp
    Processes  process list/find/kill/stop/resume/restart/details/sort
    Network    network (speeds/interfaces/connections/ping)
    Display    watch, refresh
    System     system, all, help, clear, exit

Список COMMANDS — единый источник: он же питает Command Palette (Ctrl+P)
и справку `help`. Обработчики реализованы в TUI как методы `_cmd_*`;
этот модуль только описывает команды и генерирует текст справки/палитры.
"""
from __future__ import annotations

CATEGORIES = ["Info", "Processes", "Network", "Battery", "Display", "System"]

# (команда, категория, описание, нужен ли фоновый поток)
COMMANDS = [
    ("cpu", "Info", "CPU information", True),
    ("ram", "Info", "Memory information", True),
    ("gpu", "Info", "GPU information", True),
    ("disk", "Info", "disk list | info X: | io", True),
    ("battery", "Battery", "Battery status", True),
    ("temp", "Info", "Temperatures", True),
    ("network", "Network", "network | connections | interfaces | speeds | ping", True),
    ("net", "Network", "alias: net [host]", True),
    ("process", "Processes", "process list | find | kill | stop | resume | restart | details | sort", True),
    ("proc", "Processes", "top processes by cpu|ram|name", True),
    ("system", "System", "System information", True),
    ("all", "System", "everything at once", True),
    ("watch", "Display", "watch cpu | network | process [name] | off", False),
    ("settings", "Display", "show settings & config path", False),
    ("refresh", "Display", "refresh dashboard now", False),
    ("help", "System", "show this help", False),
    ("clear", "System", "clear terminal output", False),
    ("exit", "System", "quit (alias: quit)", False),
]

# скрытые алиасы (не показываются в справке/палитре)
_ALIASES = {
    "quit": ("exit", ""),
}


def command_list() -> list:
    """Полный список команд палитры (без алиасов)."""
    out = []
    for cmd, cat, desc, thread in COMMANDS:
        out.append({"cmd": cmd, "cat": cat, "desc": desc, "thread": thread})
    return out


def lookup(words: list) -> dict | None:
    """Находит запись команды по первым словам (с учётом алиасов)."""
    first = (words[0] if words else "").lower()
    if first in _ALIASES:
        cmd, _ = _ALIASES[first]
    else:
        cmd = first
    for c, cat, desc, thread in COMMANDS:
        if c == cmd:
            return {"cmd": c, "cat": cat, "desc": desc, "thread": thread}
    return None


def expected_args(cmd: str) -> str:
    """Подсказка по аргументам команды (для справки по одной команде)."""
    guide = {
        "disk": "disk list | disk info C: | disk io",
        "network": "network | network connections | network interfaces | network speeds | network ping <host>",
        "net": "net [host]",
        "process": "process list [name] | process find <name|pid> | process sort cpu|ram|name |"
                   " process details <name|pid> | process kill|stop|resume|restart <name|pid>",
        "proc": "proc cpu | proc ram | proc name",
        "watch": "watch cpu | watch network | watch process [name] | watch off",
        "cpu": "cpu",
        "ram": "ram",
        "gpu": "gpu",
        "battery": "battery",
        "temp": "temp",
        "system": "system",
        "all": "all",
        "settings": "settings",
        "refresh": "refresh",
    }
    return guide.get(cmd, "")


def help_text() -> str:
    """Полная справка по группам."""
    lines = ["[bold]syscheck commands[/]"]
    for cat in CATEGORIES:
        items = [(c, d, t) for c, cc, d, t in COMMANDS if cc == cat]
        if not items:
            continue
        lines.append(f"  [dim]{cat}[/]")
        for c, d, t in items:
            lines.append(f"    [cyan]{c:<10}[/] {d}")
    lines.append("")
    lines.append("[dim]0-5 toggle panels (0 all)     ctrl+p palette     ↑↓ history[/]")
    lines.append("[dim]in processes table: Enter details, K kill, S stop, R restart, t sort, / search[/]")
    lines.append("[dim]!shell <cmd> — system shell (requires --enable-shell, per-command confirm)[/]")
    return "\n".join(lines)


def help_for(cmd: str) -> str:
    args = expected_args(cmd)
    return f"[cyan]{cmd}[/] {args}" if args else f"[dim]nothing more about '{cmd}'[/]"
