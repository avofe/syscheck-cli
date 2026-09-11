"""Тесты для безопасности !shell (shellguard) и декодирования пинга."""
import os

import pytest

from syscheck import providers
from syscheck import shellguard


@pytest.fixture
def isolated_config(monkeypatch, tmp_path):
    """Изолирует конфиг/лог shellguard в временной директории."""
    monkeypatch.setenv("SYSCHECK_CONFIG_DIR", str(tmp_path))
    shellguard.CONFIG_DIR = tmp_path
    shellguard.CONFIG_FILE = tmp_path / "config.json"
    shellguard.AUDIT_LOG = tmp_path / "shell_audit.log"
    return tmp_path


def test_disabled_by_default(isolated_config):
    assert shellguard.is_enabled() is False


def test_set_enabled_roundtrip(isolated_config):
    shellguard.set_enabled(True)
    assert shellguard.is_enabled() is True
    shellguard.set_enabled(False)
    assert shellguard.is_enabled() is False


def test_needs_first_confirmation(isolated_config):
    assert shellguard.needs_first_confirmation() is True
    shellguard.mark_warned()
    assert shellguard.needs_first_confirmation() is False


def test_run_shell_throws_when_disabled(isolated_config):
    with pytest.raises(shellguard.ShellDisabledError):
        shellguard.run_shell("echo hi")


def test_run_shell_executes_when_enabled(isolated_config):
    shellguard.set_enabled(True)
    out = shellguard.run_shell("echo hi")
    assert "hi" in out


def test_run_shell_writes_audit_log(isolated_config):
    shellguard.set_enabled(True)
    shellguard.run_shell("echo secret-command")
    log = shellguard.AUDIT_LOG.read_text(encoding="utf-8")
    assert "secret-command" in log


def test_decode_ping_output_cp866():
    # "время=32мс" закодированное в cp866
    raw = "время=32мс".encode("cp866")
    out = providers._decode_ping_output(raw)
    assert "32" in out


def test_decode_ping_output_utf8():
    raw = "time=32ms".encode("utf-8")
    out = providers._decode_ping_output(raw)
    assert "32" in out


def test_config_dir_env_var_used(monkeypatch, tmp_path):
    """SYSCHECK_CONFIG_DIR управляет директорией конфига !shell."""
    monkeypatch.setenv("SYSCHECK_CONFIG_DIR", str(tmp_path))
    import importlib
    import sys

    import syscheck.shellguard as sg
    reloaded = importlib.reload(sg)
    assert reloaded.CONFIG_DIR == tmp_path
    assert reloaded.CONFIG_FILE == tmp_path / "config.json"
