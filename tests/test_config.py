"""Тесты конфигурации syscheck (config.py)."""
import pytest

from syscheck import config


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    """Изолирует config.toml во временной директории."""
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.toml")
    config.reload()
    yield
    config.reload()


def test_defaults_without_file():
    assert config.refresh_interval() == 2.0
    assert config.watch_interval() == 2
    assert config.ping_host() == "8.8.8.8"
    assert "cpu" in config.default_panels()
    assert config.thresholds("cpu") == (75, 90)
    assert config.thresholds("mem") == (85, 90)
    assert config.thresholds("disk") == (85, 95)


def test_overrides_from_toml():
    config.CONFIG_FILE.write_text(
        'refresh_interval = 0.5\n'
        'ping_host = "1.1.1.1"\n'
        'default_panels = ["cpu", "procs"]\n'
        "[thresholds.cpu]\n"
        "warn = 40\n"
        "crit = 60\n",
        encoding="utf-8",
    )
    config.reload()
    assert config.refresh_interval() == 0.5
    assert config.ping_host() == "1.1.1.1"
    assert config.default_panels() == ["cpu", "procs"]
    assert config.thresholds("cpu") == (40, 60)
    assert config.thresholds("mem") == (85, 90)  # остальное по умолчанию


def test_broken_toml_falls_back_to_defaults():
    config.CONFIG_FILE.write_text("this is = not [ valid toml", encoding="utf-8")
    config.reload()
    assert config.refresh_interval() == 2.0
    assert config.thresholds("cpu") == (75, 90)
    assert "_error" in config.load()


def test_warn_above_crit_is_normalized():
    config.CONFIG_FILE.write_text(
        "[thresholds.cpu]\nwarn = 95\ncrit = 50\n", encoding="utf-8"
    )
    config.reload()
    warn, crit = config.thresholds("cpu")
    assert warn <= crit


def test_invalid_interval_falls_back():
    config.CONFIG_FILE.write_text('refresh_interval = "abc"\n', encoding="utf-8")
    config.reload()
    assert config.refresh_interval() == 2.0
