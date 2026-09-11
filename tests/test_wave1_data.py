"""Тесты Волны 1: структура данных для JSON-режимов."""
from syscheck.cli import _all_data
from syscheck.commands.watch import _collect


def test_all_data_has_all_sections():
    data = _all_data()
    for key in ("cpu", "ram", "disk", "net", "net_rates", "temp", "gpu", "battery", "sys"):
        assert key in data, f"нет секции {key} в all --json"


def test_watch_collect_keys():
    data = _collect()
    for key in ("cpu", "ram", "disk", "net", "procs", "proc_count", "sys"):
        assert key in data, f"нет ключа {key} в watch --json"


def test_watch_collect_cpu_nonblocking():
    """Первый/второй тик не должны блокироваться на 0.3с — percent это число."""
    data = _collect()
    assert isinstance(data["cpu"]["percent"], (int, float))
