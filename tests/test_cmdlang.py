"""Тесты командного языка syscheck."""
from syscheck import cmdlang


def test_command_list_has_expected_entries():
    cmds = {e["cmd"] for e in cmdlang.command_list()}
    for c in ("cpu", "ram", "gpu", "disk", "network", "battery",
              "process", "system", "watch", "help"):
        assert c in cmds


def test_lookup_known_and_unknown():
    assert cmdlang.lookup(["process"]).get("cmd") == "process"
    assert cmdlang.lookup(["PROCESS", "list"]).get("cmd") == "process"
    assert cmdlang.lookup(["net", "host"]) is not None
    assert cmdlang.lookup(["foo"]) is None
    assert cmdlang.lookup([]) is None


def test_help_text_is_grouped():
    text = cmdlang.help_text()
    assert "Info" in text
    assert "Processes" in text
    assert "Network" in text
    assert "ctrl+p" in text


def test_expected_args():
    assert "list" in cmdlang.expected_args("process")
    assert cmdlang.expected_args("battery") == "battery"