"""Тесты для утилитных функций."""
from syscheck.utils import (
    bytes_to_human, seconds_to_human, get_color_for_percent, make_bar,
)


def test_bytes_to_human():
    assert bytes_to_human(0) == "0 B"
    assert bytes_to_human(1024) == "1.00 KB"
    assert bytes_to_human(1024 * 1024) == "1.00 MB"
    assert "GB" in bytes_to_human(1024 ** 3)


def test_seconds_to_human():
    assert seconds_to_human(5) == "5s"
    assert seconds_to_human(65) == "1m 5s"
    assert seconds_to_human(3661) == "1h 1m 1s"
    assert "1d" in seconds_to_human(86400 + 3661)


def test_get_color_for_percent():
    assert get_color_for_percent(10) == "cyan"
    assert get_color_for_percent(50) == "cyan"
    assert get_color_for_percent(80) == "yellow"
    assert get_color_for_percent(95) == "red"
    assert get_color_for_percent(75) == "yellow"
    assert get_color_for_percent(74) == "cyan"


def test_make_bar():
    bar = make_bar(50, 10)
    # 5 filled + 5 empty ASCII characters (with rich markup)
    assert "#####" in bar.replace("[cyan]", "").replace("[/]", "")
    assert "....." in bar
    # different widths
    full = make_bar(100, 10)
    assert "##########" in full.replace("[red]", "").replace("[/]", "")
    zero = make_bar(0, 10)
    assert ".........." in zero
    # вставки цветной разметки
    assert "[red]" in make_bar(95, 10)
    assert "[yellow]" in make_bar(80, 10)
    assert "[cyan]" in make_bar(50, 10)

