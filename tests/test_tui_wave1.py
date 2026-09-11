"""Тесты Волны 1: TUI (панели по умолчанию, 0=все, t=сортировка) и !shell."""
import asyncio

import pytest

from syscheck import config
from syscheck.tui import SysCheckTUI, _shell_body


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CONFIG_FILE", tmp_path / "config.toml")
    config.reload()
    yield
    config.reload()


def test_shell_body_parsing():
    assert _shell_body("!shell echo hi") == "echo hi"
    assert _shell_body("!echo hi") == "echo hi"
    assert _shell_body("!shell") == ""
    assert _shell_body("!  df -h  ") == "df -h"


def test_default_panels_cpu_and_procs_visible(monkeypatch):
    async def scenario():
        app = SysCheckTUI()
        async with app.run_test():
            assert app.query_one("#panel-cpu").display is True
            assert app.query_one("#panel-ram").display is True
            assert app.query_one("#panel-procs").display is True
            assert app.query_one("#panel-gpu").display is False
            assert app.query_one("#panel-batt").display is False

    asyncio.run(scenario())


def test_zero_shows_all_panels():
    async def scenario():
        app = SysCheckTUI()
        async with app.run_test() as pilot:
            inp = app.query_one("#cmd")
            inp.value = "0"
            await pilot.press("enter")
            assert app.query_one("#panel-gpu").display is True
            assert app.query_one("#panel-batt").display is True
            assert app.query_one("#panel-procs").display is True

    asyncio.run(scenario())


def test_t_cycles_process_sort():
    async def scenario():
        app = SysCheckTUI()
        async with app.run_test() as pilot:
            assert app._proc_sort == "cpu"
            app._dt.focus()
            await pilot.press("t")
            assert app._proc_sort == "ram"
            await pilot.press("t")
            assert app._proc_sort == "name"
            await pilot.press("t")
            assert app._proc_sort == "cpu"

    asyncio.run(scenario())


def test_shell_disabled_does_not_pend(monkeypatch):
    monkeypatch.setattr("syscheck.shellguard.is_enabled", lambda: False)

    async def scenario():
        app = SysCheckTUI(enable_shell=False)
        async with app.run_test():
            app._handle_shell_cmd("echo hi")
            assert app._pending_shell_cmd is None

    asyncio.run(scenario())
