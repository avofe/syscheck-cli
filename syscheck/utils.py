"""Общие утилиты для форматирования и вывода.

Минималистичный стиль: без таблиц и рамок, без emoji, плоский текст
с выровненными колонками label / value. Акцентный цвет — cyan для
значений, dim для подписей.
"""
import os
from datetime import timedelta
from typing import Optional

from rich.console import Console

console = Console()

# Ширина колонки подписи по умолчанию в выровненных списках
LABEL_WIDTH = 12


def bytes_to_human(n: float) -> str:
    """Конвертирует байты в читаемый формат."""
    symbols = ("B", "KB", "MB", "GB", "TB", "PB")
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i * 10)
    for s in reversed(symbols):
        if abs(n) >= prefix[s]:
            value = float(n) / prefix[s]
            return f"{value:.2f} {s}"
    return f"{n} B"


def seconds_to_human(s: float) -> str:
    """Конвертирует секунды в читаемый формат."""
    td = timedelta(seconds=int(s))
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def get_color_for_percent(percent: float) -> str:
    """Возвращает цвет в зависимости от процента нагрузки.

    Красный/жёлтый — только для реальных предупреждений (высокая нагрузка).
    Обычные значения — нейтральный cyan.
    """
    if percent >= 90:
        return "red"
    elif percent >= 75:
        return "yellow"
    else:
        return "cyan"


def make_bar(percent: float, width: int = 12) -> str:
    """Создаёт ASCII прогресс-бар вида [####......]."""
    filled = int(width * percent / 100)
    filled = max(0, min(width, filled))
    empty = width - filled
    body = "#" * filled + "." * empty
    # цвет только при фактическом перегрузе
    if percent >= 90:
        colour = "[red]"
    elif percent >= 75:
        colour = "[yellow]"
    else:
        colour = "[cyan]"
    return f"{colour}[{body}][/]"


def kv(label: str, value: str, label_width: int = LABEL_WIDTH) -> str:
    """Формирует строку 'label<TAB>value' с выравниванием по колонке."""
    return f"{label.ljust(label_width)}{value}"


def print_kv(label: str, value: str, label_width: int = LABEL_WIDTH):
    """Печатает пару подпись-значение в плоском стиле."""
    console.print(kv(label, value, label_width))


def print_header(text: str):
    """Печатает маленький заголовок команды нижним регистром."""
    console.print(f"[dim]{text}[/]")


def print_ok(msg: str):
    """Печатает положительное сообщение с ASCII-меткой [+ ]."""
    console.print(f"  [bold green][+] [/]{msg}")


def print_warning(msg: str):
    """Печатает предупреждение с ASCII-меткой [!]. Красный/жёлтый."""
    console.print(f"  [bold yellow][!] [/]{msg}")


def print_error(msg: str):
    """Печатает ошибку с ASCII-меткой [x]."""
    console.print(f"  [bold red][x] [/]{msg}")


def print_value(label: str, value: str, colour: Optional[str] = None):
    """Печатает пару, где значение подсвечено (по умолчанию cyan)."""
    console.print(kv(label, f"[{colour or 'cyan'}]{value}[/]"))
