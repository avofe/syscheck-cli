"""Тесты для точки входа CLI (маршрутизация TUI/CLI)."""
import sys
from unittest.mock import patch

from syscheck import cli


def test_main_no_args_runs_tui():
    with patch.object(sys, "argv", ["syscheck"]):
        with patch("syscheck.tui.run") as mock_tui:
            with patch("syscheck.cli.app") as mock_app:
                cli.main()
                mock_tui.assert_called_once()
                mock_app.assert_not_called()


def test_main_with_args_runs_cli():
    with patch.object(sys, "argv", ["syscheck", "cpu"]):
        with patch("syscheck.tui.run") as mock_tui:
            with patch("syscheck.cli.app") as mock_app:
                cli.main()
                mock_app.assert_called_once()
                mock_tui.assert_not_called()
