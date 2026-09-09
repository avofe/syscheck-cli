"""РљРѕРјР°РЅРґРЅС‹Р№ СЏР·С‹Рє syscheck.

Р“СЂР°РјРјР°С‚РёРєР° СЂР°Р·РґРµР»РµРЅР° РЅР° РіСЂСѓРїРїС‹:

    Info       cpu, ram, gpu, disk, battery, temp
    Processes  process list/find/kill/stop/resume/restart/details/sort
    Network    network (speeds/interfaces/connections/ping)
    Display    watch, refresh
    System     system, all, help, clear, exit

РЎРїРёСЃРѕРє COMMANDS вЂ” РµРґРёРЅС‹Р№ РёСЃС‚РѕС‡РЅРёРє: РѕРЅ Р¶Рµ РїРёС‚Р°РµС‚ Command Palette (Ctrl+P)
Рё СЃРїСЂР°РІРєСѓ `help`. РћР±СЂР°Р±РѕС‚С‡РёРєРё СЂРµР°Р»РёР·РѕРІР°РЅС‹ РІ TUI РєР°Рє РјРµС‚РѕРґС‹ `_cmd_*`;
СЌС‚РѕС‚ РјРѕРґСѓР»СЊ С‚РѕР»СЊРєРѕ РѕРїРёСЃС‹РІР°РµС‚ РєРѕРјР°РЅРґС‹ Рё РіРµРЅРµСЂРёСЂСѓРµС‚ С‚РµРєСЃС‚ СЃРїСЂР°РІРєРё/РїР°Р»РёС‚СЂС‹.
"""
from __future__ import annotations

CATEGORIES = ["Info", "Processes", "Network", "Battery", "Display", "System"]

# (РєРѕРјР°РЅРґР°, РєР°С‚РµРіРѕСЂРёСЏ, РѕРїРёСЃР°РЅРёРµ, РЅСѓР¶РµРЅ Р»Рё С„РѕРЅРѕРІС‹Р№ РїРѕС‚РѕРє)
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

# СЃРєСЂС‹С‚С‹Рµ Р°Р»РёР°СЃС‹ (РЅРµ РїРѕРєР°Р·С‹РІР°СЋС‚СЃСЏ РІ СЃРїСЂР°РІРєРµ/РїР°Р»РёС‚СЂРµ)
_ALIASES = {
    "quit": ("exit", ""),
}


def command_list() -> list:
    """РџРѕР»РЅС‹Р№ СЃРїРёСЃРѕРє РєРѕРјР°РЅРґ РїР°Р»РёС‚СЂС‹ (Р±РµР· Р°Р»РёР°СЃРѕРІ)."""
    out = []
    for cmd, cat, desc, thread in COMMANDS:
        out.append({"cmd": cmd, "cat": cat, "desc": desc, "thread": thread})
    return out


def lookup(words: list) -> dict | None:
    """РќР°С…РѕРґРёС‚ Р·Р°РїРёСЃСЊ РєРѕРјР°РЅРґС‹ РїРѕ РїРµСЂРІС‹Рј СЃР»РѕРІР°Рј (СЃ СѓС‡С‘С‚РѕРј Р°Р»РёР°СЃРѕРІ)."""
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
    """РџРѕРґСЃРєР°Р·РєР° РїРѕ Р°СЂРіСѓРјРµРЅС‚Р°Рј РєРѕРјР°РЅРґС‹ (РґР»СЏ СЃРїСЂР°РІРєРё РїРѕ РѕРґРЅРѕР№ РєРѕРјР°РЅРґРµ)."""
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
    """РџРѕР»РЅР°СЏ СЃРїСЂР°РІРєР° РїРѕ РіСЂСѓРїРїР°Рј."""
    lines = ["[bold]syscheck commands[/]"]
    for cat in CATEGORIES:
        items = [(c, d, t) for c, cc, d, t in COMMANDS if cc == cat]
        if not items:
            continue
        lines.append(f"  [dim]{cat}[/]")
        for c, d, t in items:
            lines.append(f"    [cyan]{c:<10}[/] {d}")
    lines.append("")
    lines.append("[dim]ctrl+p  command palette     в†‘в†“ history      В· in processes table:[/]")
    lines.append("[dim]  Enter details, K kill, S stop, R restart, / search[/]")
    return "\n".join(lines)


def help_for(cmd: str) -> str:
    args = expected_args(cmd)
    return f"[cyan]{cmd}[/] {args}" if args else f"[dim]nothing more about '{cmd}'[/]"
