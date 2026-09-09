"""Экраны syscheck: Command Palette (Ctrl+P) и карточка процесса."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid
from textual.screen import Screen
from textual.widgets import Input, Static

from syscheck.palette import ACCENT, BORDER, DIM, MUTED, PANEL, TEXT, BG


def _label(cat: str) -> str:
    return {"Info": "I", "Processes": "P", "Network": "N",
            "Battery": "B", "Display": "D", "System": "S"}.get(cat, "?")


class PaletteScreen(Screen):
    """Оверлей поиска команд: печатаешь — отфильтровываются команды.

    Enter запускает лучший (верхний) результат, ↑↓ переключают,
    Esc закрывает.
    """

    CSS = """
PaletteScreen {
    background: #000000ee;
    padding: 1 10;
}
#palette {
    height: auto;
    max-height: 68%;
    border: round #252a2f;
    background: #101316;
    padding: 0 1;
}
#pal-row {
    layout: horizontal;
    height: 3;
    padding: 0 1;
    border-bottom: solid #252a2f;
}
.pal-prompt {
    width: 2;
    content-align: center middle;
    color: #8bd450;
}
#pal-input {
    border: none;
    background: transparent;
    color: #e6e9ec;
    height: 3;
}
#pal-input:focus {
    border: none;
}
#pal-list {
    height: auto;
    min-height: 3;
    padding: 0 1 1 1;
}
.pal-hint {
    height: 1;
    color: #555d66;
}
"""

    BINDINGS = [
        Binding("escape", "cancel", "Close"),
        Binding("down", "next", "Next", show=False),
        Binding("up", "prev", "Prev", show=False),
        Binding("enter", "submit", "Run", show=False),
    ]

    def __init__(self, commands: list):
        super().__init__()
        self._all = list(commands)
        self._filtered: list = list(commands)
        self._idx = 0

    def compose(self) -> ComposeResult:
        with Container(id="palette"):
            with Container(id="pal-row"):
                yield Static(">", classes="pal-prompt")
                yield Input(placeholder="filter commands…", id="pal-input")
            yield Static("", id="pal-list", classes="pal-list")
            yield Static("↵ run · ↑↓ select · esc close", classes="pal-hint")

    def on_mount(self) -> None:
        self.refresh_list()
        self.query_one("#pal-input", Input).focus()

    # --- фильтрация ---
    def _apply_filter(self) -> None:
        qtext = self.query_one("#pal-input").value.strip()
        q = qtext.lower()
        words = [w for w in q.split() if w]
        if not words:
            self._filtered = list(self._all)
        else:
            ranked = []
            for e in self._all:
                cmd = e["cmd"]
                desc = e["desc"].lower()
                hay = f"{cmd} {desc}"
                if not all(w in hay for w in words):
                    continue
                if hay.startswith(q):
                    rank = 0
                elif q in cmd:
                    rank = 1
                elif q in desc:
                    rank = 2
                else:
                    rank = 3
                ranked.append((rank, cmd, e))
            ranked.sort(key=lambda x: (x[0], x[1]))
            self._filtered = [e for _, _, e in ranked]
        self._idx = 0
        self.refresh_list()

    def refresh_list(self) -> None:
        rows = []
        for i, e in enumerate(self._filtered):
            marker = f"[{ACCENT}]›[/] " if i == self._idx else "  "
            line = (f"{marker}[{TEXT}]{e['cmd']:<12}[/]"
                    f"{e['desc']}  [#555d66]{_label(e['cat'])}/{e['cat']}[/]")
            rows.append(line)
        if not rows:
            rows.append(f"[#555d66]no matching commands[/]")
        self.query_one("#pal-list", Static).update("\n".join(rows))

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filter()

    def _selected(self) -> str | None:
        if not self._filtered:
            return None
        self._idx = min(self._idx, len(self._filtered) - 1)
        return self._filtered[self._idx]["cmd"]

    def action_submit(self) -> None:
        self._run()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._run()

    def _run(self) -> None:
        inp = self.query_one("#pal-input").value.strip()
        sel = self._selected()
        if inp:
            from syscheck import cmdlang
            if cmdlang.lookup(inp.split()) is not None:
                self.dismiss(inp)
                return
            if sel and inp.split()[0].lower() == sel:
                self.dismiss(inp)
                return
        self.dismiss(sel)

    def action_next(self) -> None:
        if self._filtered:
            self._idx = (self._idx + 1) % len(self._filtered)
            self.refresh_list()

    def action_prev(self) -> None:
        if self._filtered:
            self._idx = (self._idx - 1) % len(self._filtered)
            self.refresh_list()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ProcessDetailsScreen(Screen):
    """Карточка процесса (Enter в таблице процессов или process details)."""

    CSS = """
ProcessDetailsScreen {
    background: #000000bb;
}
#card {
    width: 70;
    max-height: 80%;
    height: auto;
    border: round #252a2f;
    background: #101316;
    padding: 0 1;
}
#card-head {
    height: 1;
    color: #8bd450;
}
#card-body {
    padding: 0 1 1 1;
}
#card-hint {
    height: 1;
    color: #555d66;
}
"""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("enter", "close", "Close"),
    ]

    def __init__(self, data: dict | None, error: str | None = None):
        super().__init__()
        self._data = data
        self._error = error

    def compose(self) -> ComposeResult:
        with Container(id="card"):
            yield Static("", id="card-head")
            yield Static("", id="card-body")
            yield Static("esc / enter — close", id="card-hint")

    def on_mount(self) -> None:
        self.query_one("#card-head", Static).update(self._render_head())
        self.query_one("#card-body", Static).update(self._render_body())
        self.query_one("#card", Container).focus()

    def _render_head(self) -> str:
        if self._data:
            name = self._data.get("name") or "?"
            return f"[bold]{name}[/]  [#555d66]pid {self._data.get('pid')}[/]"
        return "PROCESS DETAILS"

    def _render_body(self) -> str:
        if self._error:
            return f"[#e05b5b]{self._error}[/]"
        d = self._data
        from syscheck.utils import bytes_to_human, seconds_to_human

        def row(label: str, val: str) -> str:
            return f"[#555d66]{label:<10}[/] [#e6e9ec]{val}[/]"

        rows = [
            row("PID", f"{d.get('pid')}"),
            row("CPU", f"{d.get('cpu') or 0:.1f}%"),
            row("MEMORY", bytes_to_human(d.get('rss') or 0)),
            row("MEM%", f"{d.get('memory_percent') or 0:.1f}%"),
            row("THREADS", str(d.get('threads')) if d.get('threads') is not None else "—"),
            row("HANDLES", str(d.get('handles')) if d.get('handles') is not None else "—"),
            row("STATUS", d.get('status') or "?"),
            row("UPTIME", seconds_to_human(d.get('uptime_seconds') or 0)),
            row("EXE", _trunc(d.get('exe') or "—", 56)),
        ]
        cmdline = d.get("cmdline")
        if cmdline:
            joined = " ".join(cmdline)
            rows.append(row("COMMAND", _trunc(joined, 56)))
        else:
            rows.append(row("COMMAND", "[#555d66]—[/]"))
        return "\n".join(rows)

    def action_close(self) -> None:
        self.dismiss(None)


def _trunc(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"