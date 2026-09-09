"""Тесты для провайдеров данных (с подменой psutil)."""
from unittest.mock import MagicMock, patch

from syscheck import providers


def test_cpu_info(monkeypatch):
    fake_freq = MagicMock()
    fake_freq.current = 2000.0
    fake_freq.max = 3000.0
    monkeypatch.setattr(providers.psutil, "cpu_freq", lambda: fake_freq)
    monkeypatch.setattr(providers.psutil, "cpu_count", lambda logical=True: 8 if logical else 4)
    monkeypatch.setattr(providers.psutil, "cpu_percent", lambda *a, **k: 42.5)
    data = providers.cpu_info()
    assert data["percent"] == 42.5
    assert data["count_logical"] == 8
    assert data["count_physical"] == 4
    assert data["freq_current"] == 2000.0


def test_ram_info_shape(monkeypatch):
    mem = MagicMock()
    mem.total = 1024 ** 3 * 8
    mem.available = 1024 ** 3 * 2
    mem.used = 1024 ** 3 * 6
    mem.percent = 75.0
    monkeypatch.setattr(providers.psutil, "virtual_memory", lambda: mem)

    swap = MagicMock()
    swap.total = 0
    swap.used = 0
    swap.percent = 0
    monkeypatch.setattr(providers.psutil, "swap_memory", lambda: swap)

    monkeypatch.setattr(providers.psutil, "process_iter", lambda *a, **k: [])
    data = providers.ram_info()
    assert data["percent"] == 75.0
    assert data["total"] == 1024 ** 3 * 8
    assert isinstance(data["top_procs"], list)


def test_ram_info_takes_percent_threshold(monkeypatch):
    monkeypatch.setattr(providers.psutil, "virtual_memory",
                        lambda: MagicMock(total=0, available=0, used=0, percent=0))
    monkeypatch.setattr(providers.psutil, "swap_memory",
                        lambda: MagicMock(total=0, used=0, percent=0))
    procs = [
        {"pid": 1, "name": "a", "memory_percent": 5.0},
        {"pid": 2, "name": "b", "memory_percent": 0.05},
    ]
    monkeypatch.setattr(
        providers.psutil, "process_iter",
        lambda *a, **k: [MagicMock(info=p) for p in procs],
    )
    data = providers.ram_info()
    names = [p["name"] for p in data["top_procs"]]
    assert "a" in names
    assert "b" not in names


def test_disk_info(monkeypatch):
    part = MagicMock()
    part.device = "C:\\"
    part.mountpoint = "C:\\"
    monkeypatch.setattr(providers.psutil, "disk_partitions", lambda all=False: [part])
    usage = MagicMock()
    usage.total = 10 ** 9
    usage.used = 5 * 10 ** 8
    usage.free = 5 * 10 ** 8
    usage.percent = 50.0
    monkeypatch.setattr(providers.psutil, "disk_usage", lambda m: usage)
    monkeypatch.setattr(providers.psutil, "disk_io_counters", lambda: None)
    data = providers.disk_info()
    assert len(data["disks"]) == 1
    assert data["disks"][0]["device"] == "C:\\"
    assert data["disks"][0]["percent"] == 50.0

