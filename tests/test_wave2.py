"""Тесты Волны 2: nvidia-smi, ACPI-температуры, спарклайны, история."""
import subprocess
import time

import pytest

import syscheck.providers as providers
from syscheck.utils import sparkline


# --- спарклайны ------------------------------------------------------------
def test_sparkline_empty_returns_spaces():
    assert sparkline([], width=20) == " " * 20


def test_sparkline_flat_values_all_same_block():
    out = sparkline([50.0, 50.0, 50.0, 50.0])
    assert len(out) == 4
    assert len(set(out)) == 1


def test_sparkline_clips_to_width():
    values = list(range(100))
    assert len(sparkline(values, width=10)) == 10


def test_sparkline_scales_min_to_max():
    out = sparkline([0.0, 100.0])
    assert out[0] == "\u2581" and out[1] == "\u2588"


def test_sparkline_ascii_fallback():
    out = sparkline([0.0, 100.0], ascii=True)
    assert all(ord(c) < 128 for c in out)
    assert out[0] == " " and out[-1] == "@"


# --- nvidia-smi -------------------------------------------------------------
def _run_side_effect(results):
    calls = []

    def _run(*args, **kwargs):
        try:
            result = results[len(calls)]
        except IndexError:
            raise AssertionError(f"unexpected extra call: {args}")
        calls.append(args)
        if isinstance(result, BaseException):
            raise result
        return result

    return _run


def _fake_run(stdout, returncode=0):
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


def test_nvidia_smi_parses_full_line(monkeypatch):
    fake = _run_side_effect(
        [_fake_run("NVIDIA GeForce RTX 4090, 45, 68, 12288, 24564\n")]
    )
    monkeypatch.setattr(providers.subprocess, "run", fake)
    out = providers._nvidia_smi_info()
    assert out is not None
    assert out["name"] == "NVIDIA GeForce RTX 4090"
    assert out["util"] == 45.0
    assert out["temp"] == 68.0
    assert out["vram_used_gb"] == 12.0
    assert out["vram_gb"] == 24.0
    assert out["source"] == "nvidia-smi"


def test_nvidia_smi_na_fields_become_none(monkeypatch):
    fake = _run_side_effect(
        [_fake_run("NVIDIA GeForce GTX 1060, N/A, N/A, 1024, 6144\n")]
    )
    monkeypatch.setattr(providers.subprocess, "run", fake)
    out = providers._nvidia_smi_info()
    assert out["util"] is None and out["temp"] is None
    assert out["vram_used_gb"] == 1.0
    assert out["vram_gb"] == 6.0


def test_nvidia_smi_garbage_line_returns_none(monkeypatch):
    fake = _run_side_effect([_fake_run("not enough columns\n")])
    monkeypatch.setattr(providers.subprocess, "run", fake)
    assert providers._nvidia_smi_info() is None


def test_nvidia_smi_returns_none_when_missing(monkeypatch):
    monkeypatch.setattr(
        providers.subprocess, "run",
        _run_side_effect([FileNotFoundError("nvidia-smi not found")]),
    )
    assert providers._nvidia_smi_info() is None


def test_gpu_info_falls_back_to_wmi(monkeypatch):
    json_ps = '{"Name": "AMD Radeon(TM) Graphics", "AdapterRAM": 536870912}'
    fake = _run_side_effect([FileNotFoundError("no nvidia"), _fake_run(json_ps + "\n")])
    monkeypatch.setattr(providers.subprocess, "run", fake)
    providers._gpu_cache["data"] = None
    out = providers.gpu_info()
    assert out["name"] == "AMD Radeon(TM) Graphics"
    assert out["vram_gb"] == 0.5
    assert out["util"] is None and out["temp"] is None
    assert out["source"] == "wmi"


def test_gpu_info_returns_none_without_gpu(monkeypatch):
    monkeypatch.setattr(
        providers.subprocess, "run",
        _run_side_effect([FileNotFoundError("no nvidia"), FileNotFoundError("no wmi")]),
    )
    providers._gpu_cache["data"] = None
    assert providers.gpu_info()["name"] is None


# --- ACPI-температуры Windows ----------------------------------------------
def test_acpi_temps_parses_kelvin(monkeypatch):
    fake = _run_side_effect([_fake_run("3010\n3020\n")])
    monkeypatch.setattr(providers.subprocess, "run", fake)
    out = providers._windows_acpi_temps()
    assert out is not None
    entries = out["acpi"]
    assert len(entries) == 2
    assert entries[0].current == pytest.approx(27.9, abs=0.1)
    assert entries[1].current == pytest.approx(28.9, abs=0.1)
    assert entries[0].label == "ACPI zone"


def test_acpi_temps_empty_returns_none(monkeypatch):
    monkeypatch.setattr(
        providers.subprocess, "run", _run_side_effect([_fake_run("")])
    )
    assert providers._windows_acpi_temps() is None


def test_temperatures_mark_source(monkeypatch):
    monkeypatch.setattr(
        providers.subprocess, "run",
        _run_side_effect([_fake_run("normalized?")]),
    )
    data = providers.temperatures()
    assert "source" in data


# --- история для спарклайнов -----------------------------------------------
def test_network_speeds_push_history(monkeypatch):
    class _IO:
        bytes_recv = 100
        bytes_sent = 50

    providers._net_prev = None
    providers._net_down_hist.clear()
    providers._net_up_hist.clear()
    monkeypatch.setattr(providers.psutil, "net_io_counters", lambda: _IO())
    providers.network_speeds()
    _IO.bytes_recv = 400
    _IO.bytes_sent = 150
    time.sleep(0.11)
    providers.network_speeds()
    assert providers.net_history()["down"], "история заполняется"
    assert providers.net_history()["down"][-1] > 0
    assert providers.net_history()["up"][-1] > 0


def test_disk_io_speeds_push_history(monkeypatch):
    class _IO:
        read_bytes = 1000
        write_bytes = 2000

    providers._io_prev = None
    providers._disk_read_hist.clear()
    providers._disk_write_hist.clear()
    monkeypatch.setattr(providers.psutil, "disk_io_counters", lambda: _IO())
    providers.disk_io_speeds()
    _IO.read_bytes = 5000
    _IO.write_bytes = 9000
    time.sleep(0.11)
    providers.disk_io_speeds()
    assert providers.disk_history()["read"][-1] > 0
    assert providers.disk_history()["write"][-1] > 0


def test_cpu_history_caps_at_60():
    providers._cpu_hist.clear()
    for _ in range(70):
        providers._cpu_hist.append(1.0)
    assert len(providers.cpu_history()) == 60