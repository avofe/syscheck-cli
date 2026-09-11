"""Общие утилиты для форматирования и вывода.

Минималистичный стиль: без таблиц и рамок, без emoji, плоский текст
с выровненными колонками label / value. Акцентный цвет — cyan для
значений, dim для подписей.
"""
import os
import sys
from datetime import timedelta
from typing import List, Optional, Sequence

from rich.console import Console

from syscheck import config

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


def get_color_for_percent(percent: float, name: str = "cpu") -> str:
    """Возвращает цвет в зависимости от процента нагрузки.

    Красный/жёлтый — только для реальных предупреждений (пороги из конфига).
    Обычные значения — нейтральный cyan.
    """
    warn, crit = config.thresholds(name)
    if percent >= crit:
        return "red"
    elif percent >= warn:
        return "yellow"
    else:
        return "cyan"


def make_bar(percent: float, width: int = 12, name: str = "cpu") -> str:
    """Создаёт ASCII прогресс-бар вида [####......]."""
    warn, crit = config.thresholds(name)
    filled = int(width * percent / 100)
    filled = max(0, min(width, filled))
    empty = width - filled
    body = "#" * filled + "." * empty
    # цвет только при фактическом перегрузе
    if percent >= crit:
        colour = "[red]"
    elif percent >= warn:
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


_SPARK_BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"  # ▁▂▃▄▅▆▇█
_SPARK_ASCII = " .:-=+*#@"


def supports_block_chars() -> bool:
    """Может ли стандартный вывод CLI показать блочные символы (UTF-8)."""
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" in enc or enc == "cp65001"


def sparkline(values: Sequence[float], width: int = 20, ascii: bool = False) -> str:
    """ASCII-спарклайн последних `width` значений: min→max по шкале блоков.

    `ascii=True` — для терминалов без блочных символов (cp1251/866).
    Плоские данные дают одинаковые символы, пустая история — пробелы.
    """
    if not values:
        return " " * width
    chars = _SPARK_ASCII if ascii else _SPARK_BLOCKS
    data = list(values)[-width:]
    lo, hi = min(data), max(data)
    span = hi - lo or 1e-9
    out = []
    for v in data:
        idx = int((v - lo) / span * (len(chars) - 1))
        out.append(chars[idx])
    return "".join(out)
