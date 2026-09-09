"""Тесты новых провайдеров: процессы, сеть, батарея."""
import os
import time

from syscheck import providers


def test_cpu_detail_has_model():
    d = providers.cpu_detail()
    assert "model" in d
    assert d["model"]
    assert "per_cpu" in d
    assert "count_logical" in d


def test_battery_info_safe():
    b = providers.battery_info()
    # на ПК без батареи вернётся None, с батареей — словарь с percent 0..100
    if b is not None:
        assert 0 <= b["percent"] <= 100
        assert "plugged" in b


def test_network_speeds_deltas():
    s1 = providers.network_speeds()
    time.sleep(0.1)
    s2 = providers.network_speeds()
    assert isinstance(s1["down"], (int, float))
    assert isinstance(s2["down"], (int, float))
    assert isinstance(s2["up"], (int, float))


def test_connections_by_process_shape():
    c = providers.connections_by_process()
    assert c["total"] >= 0
    assert isinstance(c["top"], list)
    if c["top"]:
        name, count = c["top"][0]
        assert name
        assert count >= 1


def test_process_detail_self():
    d = providers.process_detail(os.getpid())
    assert d is not None
    assert d["pid"] == os.getpid()
    assert d["name"]
    assert d["rss"] > 0
    assert d["uptime_seconds"] >= 0


def test_find_process_by_pid_and_name():
    pid = os.getpid()
    assert providers.find_process(str(pid))["pid"] == pid
    assert providers.resolve_pid(str(pid)) == pid


def test_list_processes_sort_options():
    for sort in ("cpu", "ram", "name"):
        rows = providers.list_processes(sort=sort, limit=5)
        assert len(rows) <= 5
        assert all("pid" in r for r in rows)


def test_kill_self_refuses():
    try:
        providers.kill_process(os.getpid())
        assert False, "должен был отказаться убивать себя"
    except ValueError as e:
        assert "self" in str(e)