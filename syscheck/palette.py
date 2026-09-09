"""Палитра WinMon и графические примитивы (bar)."""

BG = "#0b0d0f"
PANEL = "#101316"
BORDER = "#252a2f"
TEXT = "#e6e9ec"
MUTED = "#7d858e"
DIM = "#555d66"
ACCENT = "#8bd450"
WARN = "#e4b84c"
DANGER = "#e05b5b"
BLUE = "#62a8ff"
TRACK = "#20252a"
TERM_BG = "#080a0c"


def color_for(pct: float) -> str:
    """Цвет нагрузки: зелёный/жёлтый/красный по порогам 75/90."""
    if pct >= 90:
        return DANGER
    if pct >= 75:
        return WARN
    return ACCENT


def bar_pct(pct: float, width: int = 26) -> str:
    """Горизонтальный бар █/░ с цветом нагрузки (markup)."""
    w = int(width * min(max(pct, 0), 100) / 100)
    c = color_for(pct)
    return f"[{c}]{'█' * w}[/][{TRACK}]{'░' * (width - w)}[/]"