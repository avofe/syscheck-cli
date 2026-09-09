"""Интерактивный TUI syscheck — dash-дизайн в стиле WinMon.

Запуск без аргументов открывает экран:
- дашборд: CPU, MEMORY (донут), GPU, STORAGE, NETWORK, BATTERY
  и на всю ширину — интерактивная таблица PROCESSES
- терминал команд со строкой ввода ❯ и Command Palette (Ctrl+P)

Toggle-панели (набери цифру + Enter):
  1 CPU · 2 GPU · 3 NETWORK · 4 BATTERY · 5 PROCESSES
  по умолчанию видны: MEMORY, STORAGE, NETWORK, PROCESSES

Процессы прямо в таблице:
  ↑↓ — выбор, Enter — детали, K — kill (с подтверждением),
  S — suspend, R — restart (с подтверждением), / — поиск.

!shell по умолчанию ВЫКЛЮЧЕН и включается только флагом --enable-shell.
Перед первой активацией показывается предупреждение, на каждую команду
требуется подтверждение, все выполнения пишутся в audit-лог.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime

from rich.markup import escape
from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid
from textual.widgets import DataTable, Static, Input, RichLog

from syscheck import cmdlang as cmdmod
from syscheck import providers
from syscheck import shellguard
from syscheck import __version__
from syscheck.palette import (
    ACCENT, BG, BORDER, DANGER, DIM, MUTED, PANEL, TEXT, TRACK, WARN,
    bar_pct, color_for,
)
from syscheck.screens import PaletteScreen, ProcessDetailsScreen
from syscheck.utils import bytes_to_human, seconds_to_human, get_color_for_percent, make_bar


def _rate(v: float) -> str:
    if v <= 0:
        return "[#7d858e]—[/]"
    return f"[#e6e9ec]{bytes_to_human(v)}/s[/]"


def _trunc(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _trunc_markup(s: str, n: int) -> str:
    t = Text.from_markup(s)
    if len(t.plain) <= n:
        return s
    cut = t.copy()
    cut.truncate(n)
    return str(cut)


class ProcsTable(DataTable):
    """Интерактивная таблица процессов: Enter/K/S/R//."""

    BINDINGS = [
        Binding("enter", "details", "Details", show=False),
        Binding("k", "kill_p", "Kill", show=False),
        Binding("s", "stop_p", "Stop", show=False),
        Binding("r", "restart_p", "Restart", show=False),
        Binding("/", "search_p", "Search", show=False),
    ]

    def __init__(self, tui, **kwargs):
        super().__init__(**kwargs)
        self._tui = tui

    def _pid(self) -> int | None:
        if not self.row_count:
            return None
        try:
            row = self.cursor_coordinate.row
            key = self.get_row_at(row)
            return int(key)
        except Exception:
            return None

    def action_details(self) -> None:
        self._tui.show_proc_details(self._pid())

    def action_kill_p(self) -> None:
        self._tui.prompt_proc_control("kill", self._pid())

    def action_stop_p(self) -> None:
        self._tui.proc_control("stop", self._pid())

    def action_restart_p(self) -> None:
        self._tui.prompt_proc_control("restart", self._pid())

    def action_search_p(self) -> None:
        self._tui.focus_process_search()


# ---------------------------------------------------------------------------
class SysCheckTUI(App):
    """Дашборд-оболочка в стиле WinMon."""

    TITLE = "syscheck"
    SUB_TITLE = "system diagnostics"
    ENABLE_COMMAND_PALETTE = False

    CSS = """
Screen {
    padding: 0 1;
    background: #0b0d0f;
}

#dash {
    height: 1fr;
    layout: grid;
    grid-size: 2 1;
    grid-columns: 1fr 1.4fr;
    grid-rows: 1fr;
    grid-gutter: 1;
    padding: 1 0;
}
#dash.procs-hidden {
    grid-size: 1 1;
    grid-columns: 1fr;
}

#left-col {
    height: 100%;
    layout: vertical;
}

.panel {
    border: solid #252a2f;
    background: #101316;
}
.panel.watched {
    border: solid #8bd450;
}
.panel > .ph {
    height: 1;
    padding: 0 1;
    color: #555d66;
    border-bottom: solid #252a2f;
}
.panel > .pb {
    height: 1fr;
    padding: 0 1 1 1;
}
#panel-procs {
    width: 100%;
}

#dt-procs {
    height: 1fr;
    padding: 0 1;
    border: none;
}
#dt-procs:focus {
    border: solid #353b42;
}
#dt-procs > .datatable--cursor {
    background: #14181c;
    color: #e6e9ec;
}

#log {
    height: 8;
    border: solid #252a2f;
    background: #080a0c;
    padding: 0 1;
}
#log .scrollbar {
    color: #252a2f;
}

#cmdline {
    height: 3;
    layout: horizontal;
    border: solid #252a2f;
    background: #080a0c;
    padding: 0 1;
    margin-bottom: 1;
}
.prompt {
    width: 2;
    content-align: center middle;
    color: #8bd450;
}
#cmd {
    border: none;
    background: transparent;
    color: #e6e9ec;
}
#cmd:focus {
    border: none;
}
.hints {
    dock: right;
    width: auto;
    content-align: right middle;
    color: #555d66;
}
"""

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_log", "Clear"),
        Binding("ctrl+p", "palette", "Palette"),
        Binding("up", "history_up", "Prev", show=False),
        Binding("down", "history_down", "Next", show=False),
    ]

    history: list = []

    WATCH_PANELS = {"cpu": "#panel-cpu", "network": "#panel-net", "process": "#panel-procs"}

    _TOGGLE_MAP = {"1": "cpu", "2": "gpu", "3": "net", "4": "batt", "5": "procs"}
    _PANEL_NAMES = {
        "cpu": "CPU", "gpu": "GPU", "net": "NETWORK",
        "batt": "BATTERY", "procs": "PROCESSES",
    }

    def __init__(self, enable_shell: bool = False, **kwargs):
        super().__init__(**kwargs)
        self._enable_shell_requested = enable_shell
        self._pending_shell_cmd: str | None = None
        self._first_confirm_waiting = False
        self._collecting = False
        self._dash: dict | None = None
        self._hist_index = 0
        self._watch: str | None = None
        self._proc_sort = "cpu"
        self._proc_filter: str | None = None
        self._pending_proc: tuple | None = None
        self._net_peak = {"down": 1.0, "up": 1.0}

    def compose(self) -> ComposeResult:
        table = ProcsTable(self, id="dt-procs", cursor_type="row", zebra_stripes=False)
        table.add_columns("PID", "PROCESS", "CPU", "MEMORY", "STATUS")
        self._dt = table
        yield Grid(
            Container(
                self._panel("cpu", "CPU"),
                self._panel("ram", "MEMORY"),
                self._panel("gpu", "GPU"),
                self._panel("disk", "STORAGE"),
                self._panel("net", "NETWORK"),
                self._panel("batt", "BATTERY"),
                id="left-col",
            ),
            Container(
                Static("PROCESSES", id="ph-procs", classes="ph"),
                table,
                id="panel-procs",
                classes="panel",
            ),
            id="dash",
        )
        yield RichLog(id="log", markup=True, wrap=False, min_width=40, max_lines=300)
        with Container(id="cmdline"):
            yield Static("❯", classes="prompt")
            yield Input(placeholder="ram, disk, process list, network connections, watch network, help …", id="cmd")
            yield Static("", classes="hints", id="hints")

    def _panel(self, pid: str, title: str) -> Container:
        return Container(
            Static(title, id=f"ph-{pid}", classes="ph"),
            Static("…", id=f"body-{pid}", classes="pb"),
            id=f"panel-{pid}",
            classes="panel",
        )

    def on_mount(self) -> None:
        self._log = self.query_one("#log", RichLog)
        self._write("[#8bd450][+] syscheck[/] [dim]v{0} — interactive diagnostics[/]".format(__version__))
        self._write("[dim]type 'help' for commands · ctrl+p palette · ctrl+c to exit[/]")
        self._write("[dim]1-5 toggle panels (1cpu 2gpu 3net 4batt 5proc) · ctrl+p palette[/]")
        try:
            dt = self._dt
            widths = {"PID": 6, "PROCESS": 26, "CPU": 9, "MEMORY": 10, "STATUS": 9}
            for name, w in widths.items():
                try:
                    dt.columns[name].width = w
                except Exception:
                    pass
        except Exception:
            pass
        for name in ("cpu", "gpu", "batt"):
            try:
                self.query_one(f"#panel-{name}").display = False
            except Exception:
                pass
        self._apply_watch()
        self.set_interval(2.0, self._refresh_dashboard)
        self._refresh_dashboard()
        if self._enable_shell_requested:
            self._activate_shell()
        self.query_one("#cmd", Input).focus()

    # --- toggle панелей ---
    def _toggle_panel(self, name: str) -> None:
        try:
            w = self.query_one(f"#panel-{name}")
        except Exception:
            return
        w.display = not w.display
        label = self._PANEL_NAMES.get(name, name)
        state = "shown" if w.display else "hidden"
        self._write(f"[dim]{label}: {state}[/]")
        if name == "procs":
            dash = self.query_one("#dash")
            dash.set_class(not w.display, "procs-hidden")
        self._apply_watch()

    # --- лог команд ---
    def _write(self, text: str) -> None:
        for line in text.split("\n"):
            if line.strip():
                self._log.write(f"[#555d66]›[/] {line}")
            else:
                self._log.write("")

    def _clear_log(self) -> None:
        self._log.clear()

    # --- дашборд: фоновый сбор в потоке, рендер из кэша ---
    def _refresh_dashboard(self) -> None:
        if self._collecting:
            return
        self._collecting = True
        try:
            asyncio.create_task(self._tick())
        except RuntimeError:
            self._collecting = False

    async def _tick(self) -> None:
        try:
            data = await asyncio.to_thread(self._collect)
        except Exception:
            data = None
        finally:
            self._collecting = False
        if data is None:
            return
        self._dash = data
        try:
            self.query_one("#hints", Static).update("1\u20115 panels \u00b7 ctrl+p palette")
            self.query_one("#body-cpu", Static).update(self._cpu_body(data["cpu"], data["temp"]))
            self.query_one("#body-ram", Static).update(self._mem_body(data["ram"]))
            self.query_one("#body-gpu", Static).update(self._gpu_body(data["gpu"]))
            self.query_one("#body-disk", Static).update(self._disk_body(data["disk"], data["io"]))
            self.query_one("#body-net", Static).update(self._net_body(data["net_rates"], data["conn"], data["net"]))
            self.query_one("#body-batt", Static).update(self._batt_body(data["batt"]))
            self.query_one("#ph-procs", Static).update(self._procs_header(data))
            self._update_procs_table(self._render_procs(data))
        except Exception:
            pass
        self._apply_watch()

    def _collect(self) -> dict:
        delta = providers.cpu_delta()
        base = providers.cpu_info(interval=None)
        cpu = dict(base)
        if delta is not None:
            cpu["percent"], cpu["per_cpu"] = delta
        return {
            "cpu": cpu,
            "ram": providers.ram_info(top=False),
            "net": providers.net_info(),
            "net_rates": providers.network_speeds(),
            "disk": providers.disk_info(),
            "sys": providers.system_info(),
            "procs": providers.list_processes(sort=self._proc_sort, limit=80),
            "proc_count": providers.process_count(),
            "gpu": providers.gpu_info(),
            "io": providers.disk_io_speeds(),
            "conn": providers.connections_by_process(),
            "batt": providers.battery_info(),
            "temp": providers.cpu_temp_celsius(),
            "clock": datetime.now().strftime("%H:%M:%S"),
        }

    # --- рендеры панелей ---
    def _metric_line(self, big: str, label: str) -> str:
        return f"{big}  [#7d858e]{label}[/]"

    def _cpu_body(self, d: dict, temp: float | None) -> str:
        freq = d.get("freq_current") or 0
        ghz = f"{freq / 1000:.2f} GHz" if freq else "\u2014"
        t = f"{temp:.0f}\u00b0C" if temp is not None else "\u2014"
        return "\n".join([
            self._metric_line(f"[{color_for(d['percent'])}]{d['percent']:3.0f}[/][#7d858e] %[/]", "TOTAL USAGE"),
            bar_pct(d["percent"], 22),
            f"[#555d66]FREQ[/] {ghz}"
            f"   [#555d66]CORES[/] [#e6e9ec]{d['count_physical']}p/{d['count_logical']}l[/]"
            f"   [#555d66]TEMP[/] [#e6e9ec]{t}[/]",
        ])

    def _mem_body(self, d: dict) -> str:
        def row(label: str, val: str) -> str:
            return f"[#555d66]{label:<9}[/] [#e6e9ec]{val}[/]"

        lines = [
            self._metric_line(
                f"[{color_for(d['percent'])}]{d['percent']:3.0f}[/][#7d858e] %[/]",
                "TOTAL USAGE",
            ),
            bar_pct(d["percent"], 22),
            row("TOTAL", f"{bytes_to_human(d['total']):>9}"),
            row("USED", f"{bytes_to_human(d['used']):>9}"),
            row("AVAILABLE", f"{bytes_to_human(d['available']):>9}"),
            row("CACHED", f"{bytes_to_human(d['cached']):>9}"),
        ]
        if d["swap_total"] > 0:
            lines.append(row("SWAP", f"{d['swap_percent']:.0f}% {bytes_to_human(d['swap_total']):>7}"))
        return "\n".join(lines)

    def _gpu_body(self, g: dict) -> str:
        name = g.get("name")
        if not name:
            return "[#7d858e]no GPU info detected[/]"
        name = _trunc(name, 34)
        vram = g.get("vram_gb")
        vram_txt = f"{vram:.1f} / {vram:.1f} GB" if vram else "\u2014"
        util, temp = g.get("util"), g.get("temp")
        lines = [
            self._metric_line(
                f"[#e6e9ec]{util:.0f}[/][#7d858e] %[/]" if util is not None else "[#e6e9ec]N/A[/]",
                "UTILIZATION",
            ),
        ]
        if util is not None:
            lines.append(bar_pct(util, 22))
        else:
            lines.append(bar_pct(0, 22))
        lines.append(f"[#555d66]GPU[/] [#7d858e]{name}[/]")
        t_txt = f"{temp}\u00b0C" if temp is not None else "\u2014"
        lines.append(f"[#555d66]TEMP[/] [#7d858e]{t_txt}[/]   [#555d66]VRAM[/] [#e6e9ec]{vram_txt}[/]")
        return "\n".join(lines)

    def _disk_body(self, d: dict, io: dict) -> str:
        disks = d.get("disks") or []
        if not disks:
            return "[#7d858e]no disks[/]"
        lines = []
        for disk in disks[:2]:
            dev = escape(disk["device"].rstrip("\\"))
            c = color_for(disk["percent"])
            lines.append(
                f"[#e6e9ec]{dev}[/] {bar_pct(disk['percent'], 16)}"
                f"  [{c}]{disk['percent']:3.0f}%[/]"
            )
        lines.append(
            f"[#555d66]READ[/] {_rate(io.get('read', 0))}"
            f"  [#555d66]WRITE[/] {_rate(io.get('write', 0))}"
        )
        return "\n".join(lines)

    def _net_body(self, rates: dict, conn: dict, net: dict) -> str:
        up_ifaces = [i for i in net.get("interfaces", []) if i["up"] and i["ipv4"]]
        if up_ifaces:
            itf = up_ifaces[0]
            top = f"[#7d858e]INTERFACE[/] [#e6e9ec]{_trunc(itf['name'], 12)}[/]"
            top += f"  [#7d858e]IP[/] [#e6e9ec]{itf['ipv4'][0]}[/]"
        else:
            top = "[#7d858e]no interfaces up[/]"
        down = rates.get("down") or 0
        up = rates.get("up") or 0
        self._net_peak["down"] = max(self._net_peak["down"], down)
        self._net_peak["up"] = max(self._net_peak["up"], up)
        dw = int(20 * min(down / self._net_peak["down"], 1))
        uw = int(20 * min(up / self._net_peak["up"], 1))
        total = conn.get("total", 0)
        return "\n".join([
            top,
            ("[#555d66]DOWNLOAD[/] " + _rate(down) + f"  [{ACCENT}]{'█' * dw}[/][{TRACK}]{'░' * (20 - dw)}[/]"),
            ("[#555d66]UPLOAD[/]   " + _rate(up) + f"  [{ACCENT}]{'█' * uw}[/][{TRACK}]{'░' * (20 - uw)}[/]"),
            f"[#555d66]CONNECTIONS[/] [#e6e9ec]{total}[/]",
        ])

    def _batt_body(self, b: dict | None) -> str:
        if not b:
            return "[#7d858e]no battery detected[/]"
        lines = [
            self._metric_line(f"[{color_for(b['percent'])}]{b['percent']:3.0f}[/][#7d858e] %[/]", "CHARGE"),
            bar_pct(b["percent"], 22),
        ]
        state = "PLUGGED IN" if b.get("plugged") else "DISCHARGING"
        left = ""
        if b.get("seconds_left"):
            left = f"  \u00b7 {int(b['seconds_left'] / 60)}m left"
        lines.append(f"[#555d66]{state}[/]{left}")
        return "\n".join(lines)

    # --- процессы ---
    def _procs_header(self, d: dict) -> str:
        head = f"PROCESSES  [#7d858e]{d['proc_count']} RUNNING[/]"
        if self._proc_filter:
            head += f"  [#555d66]filter[/] [{ACCENT}]{_trunc(self._proc_filter, 12)}[/]"
        head += f"  [#555d66]\u00b7 sort {self._proc_sort}[/]"
        if self._watch == "process":
            head += f"  [{ACCENT}]● watching[/]"
        return head

    def _render_procs(self, d: dict) -> list:
        data = d.get("procs") or []
        if self._proc_filter:
            q = self._proc_filter.lower()
            data = [p for p in data if q in (p.get("name") or "").lower()
                    or q == str(p.get("pid"))]
        sort_key = {"cpu": "cpu_percent", "ram": "memory_percent", "name": "name"}.get(
            self._proc_sort, "cpu_percent")
        if sort_key == "name":
            data = sorted(data, key=lambda x: (x.get(sort_key) or "") or "")
        else:
            data = sorted(data, key=lambda x: x.get(sort_key, 0) or 0, reverse=True)
        return data[:15]

    def _update_procs_table(self, rows: list) -> None:
        dt = self._dt
        prev_key: str | None = None
        if dt.row_count:
            try:
                prev_key = dt.get_row_at(dt.cursor_coordinate.row)
            except Exception:
                prev_key = None
        dt.clear()
        for p in rows:
            pid = p.get("pid") or 0
            name = _trunc(p.get("name") or "?", 26)
            cpu = min(p.get("cpu_percent") or 0, 9999)
            rss = p.get("rss") or 0
            st = (p.get("status") or "running").lower()[:9]
            sc = {"running": ACCENT, "stopped": DANGER, "sleeping": MUTED}.get(st, MUTED)
            dt.add_row(
                Text(f"{pid}", style=TEXT),
                Text(name, style=TEXT),
                Text(f"{cpu:5.1f}%", style=color_for(cpu)),
                Text(bytes_to_human(rss), style=TEXT),
                Text(st.upper(), style=sc),
                key=str(pid),
            )
        if rows and dt.row_count:
            if prev_key:
                try:
                    dt.move_cursor(row=dt.get_row_index(prev_key), column=0)
                    return
                except Exception:
                    pass
            dt.move_cursor(row=0, column=0)

    def show_proc_details(self, pid: int | None) -> None:
        if pid is None:
            self._write("[dim]no process selected[/]")
            return
        try:
            asyncio.create_task(self._collect_and_show(pid))
        except RuntimeError:
            pass

    def prompt_proc_control(self, kind: str, pid: int | None) -> None:
        if pid is None:
            self._write("[dim]no process selected[/]")
            return
        self._pending_proc = (kind, pid)
        guard = "self" if pid == os.getpid() else None
        self._write(f"[yellow]confirm {kind} of process {pid}? type 'confirm'[/]" +
                    (f"  [red](refusing self!)[/] " if guard else ""))

    def proc_control(self, kind: str, pid: int | None) -> None:
        if pid is None:
            self._write("[dim]no process selected[/]")
            return
        if kind in ("stop", "resume"):
            self._run_in_thread(lambda: self._proc_ctl_op(kind, pid))

    def focus_process_search(self) -> None:
        inp = self.query_one("#cmd", Input)
        inp.value = "process find "
        inp.focus()
        inp.cursor_position = len(inp.value)

    def _proc_ctl_op(self, kind: str, pid: int) -> str:
        fn = {"kill": providers.kill_process, "restart": providers.restart_process,
              "stop": providers.suspend_process, "resume": providers.resume_process}[kind]
        try:
            if pid == os.getpid():
                return "[red]refusing to act on self[/]"
            r = fn(pid)
            return f"[#8bd450][+] {r} (pid {pid})[/]"
        except Exception as e:
            return f"[red]error: {e}[/]"

    async def _collect_and_show(self, pid: int) -> None:
        data = await asyncio.to_thread(providers.process_detail, pid)
        self.push_screen(ProcessDetailsScreen(
            data, error=None if data else f"process {pid} not found"))

    # --- фокус-watch ---
    def _apply_watch(self) -> None:
        for key, sel in self.WATCH_PANELS.items():
            try:
                w = self.query_one(sel)
                w.set_class(self._watch == key, "watched")
            except Exception:
                pass

    # --- Command Palette ---
    def action_palette(self) -> None:
        self.push_screen(PaletteScreen(cmdmod.command_list()), callback=self._palette_picked)

    def _palette_picked(self, cmd: str | None) -> None:
        if not cmd:
            return
        self._run_command(cmd)

    # --- активация !shell ---
    def _activate_shell(self) -> None:
        if shellguard.needs_first_confirmation():
            self._first_confirm_waiting = True
            self._write("[bold red][!] !shell is DISABLED by default[/]")
            self._write(shellguard.WARNING_TEXT.format(audit=shellguard.AUDIT_LOG))
            self._write("[yellow]type 'yes' to enable !shell, or anything else to keep it disabled[/]")
        else:
            shellguard.set_enabled(True)
            self._mark_shell_enabled()

    def _mark_shell_enabled(self) -> None:
        self._write("[#8bd450][+] !shell enabled[/]")
        self._write(f"[dim]every command is confirmed and logged to {shellguard.AUDIT_LOG}[/]")

    # --- обработка ввода ---
    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        event.input.value = ""
        if not raw:
            return

        if self._first_confirm_waiting:
            self._handle_first_confirm(raw)
            return
        if self._pending_shell_cmd is not None:
            self._handle_shell_confirm(raw)
            return
        if self._pending_proc is not None:
            self._handle_proc_confirm(raw)
            return

        if raw in self._TOGGLE_MAP:
            self._toggle_panel(self._TOGGLE_MAP[raw])
            return

        self.history.append(raw)
        self._hist_index = len(self.history)
        self._write(f"[#7d858e]❯[/] [bold]{raw}[/]")
        self._run_command(raw)

    def _run_command(self, raw: str) -> None:
        words = raw.split()
        cmd0 = words[0].lower() if words else ""
        if cmd0 in ("exit", "quit"):
            self.exit()
            return
        if cmd0 == "clear":
            self._clear_log()
            return
        if cmd0 == "help":
            self._write(cmdmod.help_text())
            return
        if cmd0 == "watch":
            self._write(self._cmd_watch(words[1:]))
            return
        if cmd0 == "refresh":
            self._refresh_dashboard()
            return
        if cmd0 == "settings":
            self._write(self._cmd_settings())
            return

        entry = cmdmod.lookup(words)
        if entry is None:
            self._write(f"[dim]unknown command:[/] {cmd0}")
            self._write("[dim]type 'help' for a list[/]")
            return
        fn = self._handler_for(entry["cmd"])
        if fn is None:
            self._write(f"[dim]unknown command:[/] {cmd0}")
            return
        if entry["thread"]:
            self._run_in_thread(lambda: fn(words[1:]))
        else:
            out = fn(words[1:])
            if out:
                self._write(out)

    def _handler_for(self, cmd: str):
        return {
            "cpu": self._cmd_cpu, "ram": self._cmd_ram, "gpu": self._cmd_gpu,
            "battery": self._cmd_battery, "temp": self._cmd_temp,
            "disk": self._cmd_disk, "network": self._cmd_network,
            "net": self._cmd_net, "process": self._cmd_process, "proc": self._cmd_proc,
            "system": self._cmd_system, "all": self._cmd_all,
        }.get(cmd)

    def _run_in_thread(self, fn, note: str | None = None) -> None:
        async def run() -> None:
            if note:
                self._write(note)
            try:
                result = await asyncio.to_thread(fn)
            except Exception as e:
                self._write(f"[red]error: {e}[/]")
                return
            if isinstance(result, tuple) and result and result[0] == "@details":
                pid = result[1]
                data = await asyncio.to_thread(providers.process_detail, None if pid is None else int(pid))
                self.push_screen(ProcessDetailsScreen(
                    data, error=None if data else f"process {pid} not found"))
                return
            self._write(result)

        try:
            asyncio.create_task(run())
        except RuntimeError:
            self._write("[red]error: app loop not running[/]")

    def _handle_shell_cmd(self, args) -> None:
        shell_cmd = " ".join(args)
        if not shell_cmd:
            self._write("[dim]usage: !shell <command>[/]")
            return
        if not shellguard.is_enabled():
            self._write("[yellow][!] !shell is disabled[/]")
            self._write("[dim]run syscheck with --enable-shell to turn it on[/]")
            return
        self._pending_shell_cmd = shell_cmd
        self._write(shellguard.resolve_confirmation(shell_cmd))

    def _handle_shell_confirm(self, raw: str) -> None:
        cmd = self._pending_shell_cmd
        self._pending_shell_cmd = None
        if raw == cmd or raw.lower() == "confirm":
            self._write(f"[dim]> !shell {cmd}[/]")
            self._run_in_thread(lambda: shellguard.run_shell(cmd))
        else:
            self._write(f"[dim]cancelled ({raw})[/]")

    def _handle_first_confirm(self, raw: str) -> None:
        self._first_confirm_waiting = False
        if raw.lower() == "yes":
            shellguard.set_enabled(True)
            shellguard.mark_warned()
            self._mark_shell_enabled()
        else:
            self._write(f"[dim]!shell stays disabled ({raw})[/]")

    def _handle_proc_confirm(self, raw: str) -> None:
        kind, pid = self._pending_proc
        self._pending_proc = None
        if raw == "confirm":
            self._write(f"[dim]> process {kind} {pid}[/]")
            self._run_in_thread(lambda: self._proc_ctl_op(kind, pid))
        else:
            self._write(f"[dim]cancelled ({raw})[/]")

    # --- команды: Info ---
    def _cmd_cpu(self, args) -> str:
        d = providers.cpu_detail()
        t = f"{d['temp']:.0f}\u00b0C" if d.get("temp") is not None else "\u2014"
        ghz = f"{d['freq_current'] / 1000:.2f} GHz" if d.get("freq_current") else "\u2014"
        lines = [
            "[dim]CPU DETAILS[/]",
            f"[#555d66]{'Model':<9}[/] [#e6e9ec]{_trunc(d['model'], 52)}[/]",
            f"[#555d66]{'Cores':<9}[/] [#e6e9ec]{d['count_physical']} / {d['count_logical']}[/]",
            f"[#555d66]{'Frequency':<9}[/] [#e6e9ec]{ghz}[/]",
            f"[#555d66]{'Temperature':<9}[/] [#e6e9ec]{t}[/]",
            "[dim]per-core[/]",
        ]
        for i, p in enumerate(d.get("per_cpu") or []):
            lines.append(f"  Core {i:<2} {bar_pct(p, 12)}  [{color_for(p)}]{p:3.0f}%[/]")
        return "\n".join(lines)

    def _cmd_ram(self, args) -> str:
        d = providers.ram_info()
        lines = [
            "[dim]MEMORY[/]",
            f"[#555d66]{'Used':<9}[/] [{color_for(d['percent'])}]{bytes_to_human(d['used'])}[/] / {bytes_to_human(d['total'])}  ({d['percent']:.0f}%)",
            f"[#555d66]{'Available':<9}[/] [#e6e9ec]{bytes_to_human(d['available'])}[/]",
            f"[#555d66]{'Cached':<9}[/] [#e6e9ec]{bytes_to_human(d['cached'])}[/]",
        ]
        if d["swap_total"] > 0:
            lines.append(f"[#555d66]{'Swap':<9}[/] {d['swap_percent']:.0f}% ({bytes_to_human(d['swap_total'])})")
        lines.append(bar_pct(d["percent"], 20))
        return "\n".join(lines)

    def _cmd_gpu(self, args) -> str:
        g = providers.gpu_info()
        if not g.get("name"):
            return "[dim]GPU[/]\n[#7d858e]no GPU info detected[/]"
        lines = ["[dim]GPU[/]", f"[#e6e9ec]{g['name']}[/]"]
        if g.get("vram_gb"):
            lines.append(f"[#555d66]{'VRAM':<9}[/] [#e6e9ec]{g['vram_gb']:.1f} GB[/]")
        if g.get("util") is not None:
            lines.append(f"[#555d66]{'Util':<9}[/] {g['util']:.0f}%  {bar_pct(g['util'], 16)}")
        if g.get("temp") is not None:
            lines.append(f"[#555d66]{'Temp':<9}[/] [#e6e9ec]{g['temp']}\u00b0C[/]")
        if g.get("util") is None and g.get("temp") is None:
            lines.append("[#7d858e]utilization/temp not exposed by this driver[/]")
        return "\n".join(lines)

    def _cmd_battery(self, args) -> str:
        b = providers.battery_info()
        if not b:
            return "[dim]battery[/]\n[#7d858e]no battery detected[/]"
        lines = ["[dim]battery[/]",
                 f"[#555d66]{'Charge':<9}[/] [{color_for(b['percent'])}]{b['percent']:.0f}%[/]"]
        lines.append(bar_pct(b["percent"], 20))
        lines.append(f"[#555d66]{'State':<9}[/] [{'#8bd450' if b.get('plugged') else '#e4b84c'}]{'CHARGING/PLUGGED' if b.get('plugged') else 'DISCHARGING'}[/]")
        if b.get("seconds_left"):
            lines.append(f"[#555d66]{'Remaining':<9}[/] {int(b['seconds_left'] / 60)}m")
        return "\n".join(lines)

    def _cmd_temp(self, args) -> str:
        d = providers.temperatures()
        if not d["available"]:
            return "[#7d858e]temperatures not supported via psutil on this system[/]"
        lines = ["[dim]temperatures[/]"]
        for name, entries in d["temps"].items():
            for e in entries:
                lines.append(f"  [#7d858e]{_trunc(name, 24)}[/] [#e6e9ec]{e.current}\u00b0C[/]")
        return "\n".join(lines) if len(lines) > 1 else "no sensors"

    # --- команды: Network ---
    def _cmd_network(self, args) -> str:
        sub = args[0].lower() if args else ""
        if sub == "connections":
            c = providers.connections_by_process()
            lines = ["[dim]TCP CONNECTIONS[/]",
                     f"  [#555d66]total[/] [#e6e9ec]{c['total']}[/]"]
            for name, n in c["top"]:
                lines.append(f"  {_trunc(name, 24):<26}[#e6e9ec]{n:>4}[/]")
            return "\n".join(lines)
        if sub == "interfaces":
            d = providers.net_info()
            lines = ["[dim]NETWORK INTERFACES[/]"]
            for i in d["interfaces"]:
                st = "[#8bd450]up[/]" if i["up"] else "[#555d66]down[/]"
                ip = ", ".join(i["ipv4"]) if i["ipv4"] else "[#555d66]\u2014[/]"
                lines.append(f"  {st}  {_trunc(i['name'], 20):<22}{ip:<18}{i['speed']} Mbps")
            return "\n".join(lines)
        if sub == "speeds":
            r = providers.network_speeds()
            return ("[dim]NETWORK SPEEDS[/]\n"
                    f"  [#555d66]download[/] {_rate(r['down'])}\n"
                    f"  [#555d66]upload[/]   {_rate(r['up'])}")
        if sub in ("ping", "icmp"):
            host = args[1] if len(args) > 1 else "8.8.8.8"
            return self._net([host])
        if sub == "help":
            return self._net([])
        return self._net([])

    def _cmd_net(self, args) -> str:
        return self._net(args)

    def _net(self, args) -> str:
        host = args[0] if args else "8.8.8.8"
        d = providers.net_info()
        lines = []
        for i in d["interfaces"]:
            st = "[#8bd450]up[/]" if i["up"] else "[#555d66]down[/]"
            ip = ", ".join(i["ipv4"]) if i["ipv4"] else "[#555d66]N/A[/]"
            lines.append(f"  {st}  {_trunc(i['name'], 20).ljust(20)} {ip}  {i['speed']} Mbps")
        if d["io"]:
            lines.append(f"[#555d66]traffic[/] [#8bd450]{bytes_to_human(d['io']['bytes_sent'])}[/] / {bytes_to_human(d['io']['bytes_recv'])}")
        p = providers.ping(host)
        if p["success"] and p["avg_ms"] is not None:
            lines.append(f"[#8bd450]ping {host}: {p['avg_ms']:.1f} ms[/]")
        elif p["success"]:
            lines.append(f"[#8bd450]ping {host}: ok[/]")
        else:
            lines.append(f"[#e05b5b]ping {host}: unreachable[/]")
        return "\n".join(lines)

    # --- команды: Processes ---
    def _cmd_process(self, args) -> str:
        sub = args[0].lower() if args else "list"
        rest = args[1:]
        if sub == "list":
            return self._proc_table_text(rest)
        if sub == "find":
            if not rest:
                return "[dim]usage: process find <name|pid>[/]"
            p = providers.find_process(rest[0])
            if not p:
                return f"[#7d858e]no process matching '{rest[0]}'[/]"
            return (f"[#8bd450][+] {_trunc(p['name'], 20)}[/] pid {p['pid']}"
                    f"  cpu {p['cpu']:.1f}%  mem {p['memory_percent']:.1f}%"
                    f"\n[dim]  \u2192 process details {p['pid']} or find it in the table[/]")
        if sub == "sort":
            key = rest[0].lower() if rest else "cpu"
            if key not in ("cpu", "ram", "name"):
                return f"[dim]sort by cpu|ram|name, not '{key}'[/]"
            self._proc_sort = key
            return f"processes sorted by {key}"
        if sub in ("kill", "killall", "stop", "suspend", "resume", "restart"):
            if not rest:
                return f"[dim]usage: process {sub} <name|pid>[/]"
            pid = providers.resolve_pid(rest[0])
            if pid is None:
                return f"[#7d858e]no process matching '{rest[0]}'[/]"
            if sub == "kill" or sub == "restart":
                self._pending_proc = (sub, pid)
                return f"[yellow]confirm {sub} of process {pid}? type 'confirm'[/]"
            return self._proc_ctl_op("stop" if sub in ("stop", "suspend") else "resume", pid)
        if sub == "details":
            if not rest:
                return "[dim]usage: process details <name|pid>[/]"
            pid = providers.resolve_pid(rest[0])
            if pid is None:
                return f"[#7d858e]no process matching '{rest[0]}'[/]"
            return ("@details", pid)
        return self._proc_table_text([])

    def _proc_table_text(self, args, sort: str | None = None) -> str:
        q = args[0] if args else None
        key = sort or self._proc_sort
        rows = providers.list_processes(query=q, sort=key, limit=20)
        lines = [f"[dim]processes \u00b7 sort {key}" + (f" \u00b7 filter '{q}'" if q else "") + "[/]",
                 f"[#555d66]{'PID':<7}{'PROCESS':<26}{'CPU':>8}{'MEM':>9}{'STATUS':>9}[/]"]
        for p in rows:
            cpu = min(p.get("cpu_percent") or 0, 9999)
            rss = p.get("rss") or 0
            st = (p.get("status") or "running").lower()[:9]
            sc = {"running": ACCENT, "stopped": DANGER, "sleeping": MUTED}.get(st, MUTED)
            lines.append(
                f"[#7d858e]{p.get('pid') or 0:<7}[/]{_trunc((p.get('name') or '?'), 26):<26}"
                f"[{color_for(cpu)}]{cpu:6.1f}[/]"
                f"[#7d858e]%[/]"
                f"[#e6e9ec]{bytes_to_human(rss):>8}[/]"
                f"[{sc}]{st.upper():>9}[/]"
            )
        if len(lines) == 2:
            lines.append("[#7d858e]no processes[/]")
        lines.append("[dim]\u2192 click the table or tab to it: Enter details \u00b7 K kill \u00b7 S stop \u00b7 R restart \u00b7 / search[/]")
        return "\n".join(lines)

    def _cmd_proc(self, args) -> str:
        key = args[0] if args and args[0] in ("cpu", "ram", "name") else self._proc_sort
        return self._proc_table_text([], sort=key)

    # --- команды: Storage ---
    def _cmd_disk(self, args) -> str:
        sub = args[0].lower() if args else "list"
        if sub == "io":
            io = providers.disk_io_speeds()
            return ("[dim]DISK IO[/]\n"
                    f"  [#555d66]read[/]  {_rate(io['read'])}\n"
                    f"  [#555d66]write[/] {_rate(io['write'])}")
        if sub == "info":
            letter = args[1] if len(args) > 1 else ""
            return self._disk_info_letter(letter.upper())
        d = providers.disk_info()
        lines = ["[dim]DISKS[/]"]
        for disk in d["disks"]:
            c = color_for(disk["percent"])
            dev = escape(disk["device"].rstrip("\\"))
            lines.append(f"  [#e6e9ec]{dev}[/] [{c}]{disk['percent']:3.0f}%[/] {bar_pct(disk['percent'], 14)}")
            lines.append(f"      {bytes_to_human(disk['used'])} / {bytes_to_human(disk['total'])} (free {bytes_to_human(disk['free'])})")
        return "\n".join(lines) if len(lines) > 1 else "no disks"

    def _disk_info_letter(self, letter: str) -> str:
        d = providers.disk_info()
        for disk in d["disks"]:
            dev = disk["device"].rstrip("\\")
            if letter and dev.upper().startswith(letter):
                c = color_for(disk["percent"])
                return "\n".join([
                    f"[dim]DISK {dev}[/] [{c}]{disk['percent']:.0f}%[/]",
                    f"  [#555d66]total[/]  [#e6e9ec]{bytes_to_human(disk['total'])}[/]",
                    f"  [#555d66]used[/]   [#e6e9ec]{bytes_to_human(disk['used'])}[/]",
                    f"  [#555d66]free[/]   [#e6e9ec]{bytes_to_human(disk['free'])}[/]",
                    "  " + bar_pct(disk["percent"], 18),
                ])
        return f"[#7d858e]no disk starting with '{letter}'[/]"

    # --- команды: System ---
    def _cmd_system(self, args) -> str:
        return self._sys(args)

    def _sys(self, args) -> str:
        d = providers.system_info()
        q = providers.system_quick()
        lines = [
            "[dim]SYSTEM[/]",
            f"[#555d66]{'OS':<9}[/] [#e6e9ec]{d['os']}[/] ({d['machine']})",
            f"[#555d66]{'Host':<9}[/] {d['node']}",
            f"[#555d66]{'CPU':<9}[/] {_trunc(d['processor'], 40)}",
            f"[#555d66]{'Uptime':<9}[/] {seconds_to_human(d['uptime_seconds'])} (since {d['boot_datetime']})",
            f"[#555d66]{'Python':<9}[/] {d['python']}",
        ]
        if d["users"]:
            lines.append(f"[#555d66]{'Users':<9}[/] {', '.join(d['users'])}")
        lines.append(f"[#555d66]{'Load':<9}[/] cpu {q['cpu_percent']}%  "
                     f"ram {q['ram_percent']}% (free {bytes_to_human(q['ram_available'])})")
        if q.get("main_percent") is not None:
            lines.append(f"[#555d66]{'Disk':<9}[/] root {q['main_percent']}% (free {bytes_to_human(q['main_free'])})")
        net = providers.net_info()
        if net.get("io"):
            lines.append(f"[#555d66]{'Net':<9}[/] sent {bytes_to_human(net['io']['bytes_sent'])}  "
                         f"recv {bytes_to_human(net['io']['bytes_recv'])}")
        return "\n".join(lines)

    def _cmd_all(self, args) -> str:
        parts = [self._cmd_cpu([]), self._cmd_ram([]), self._cmd_disk([])]
        net_summary = self._net([]).splitlines()
        parts.append("\n".join(net_summary[:3]))
        return "\n\n".join(parts)

    # --- команды: Display ---
    def _cmd_watch(self, args) -> str:
        if not args:
            return ("[dim]usage: watch cpu | network | process [name] | off[/]\n"
                    f"[dim]currently: {self._watch or 'none'}[/]")
        target = args[0].lower()
        if target in ("off", "none", "clear"):
            self._watch = None
            self._proc_filter = None
            self._apply_watch()
            self._refresh_dashboard()
            return "watching: none"
        if target == "cpu":
            self._watch = "cpu"
        elif target == "network":
            self._watch = "network"
        elif target in ("process", "procs"):
            self._watch = "process"
            self._proc_filter = args[1] if len(args) > 1 else self._proc_filter
        else:
            return f"[dim]unknown watch target '{target}'[/]"
        self._apply_watch()
        self._refresh_dashboard()
        extra = f" filter '{self._proc_filter}'" if self._watch == "process" and self._proc_filter else ""
        return f"watching: {self._watch}{extra}"

    def _cmd_settings(self) -> str:
        cfg = os.path.expanduser("~/.syscheck/config.json")
        audit = os.path.expanduser("~/.syscheck/shell_audit.log")
        shell = "enabled" if shellguard.is_enabled() else "disabled"
        watch = self._watch or "none"
        return "\n".join([
            "[dim]SETTINGS[/]",
            f"[#555d66]{'Version':<9}[/] {__version__}",
            f"[#555d66]{'Config':<9}[/] {cfg}",
            f"[#555d66]{'Audit':<9}[/] {audit}",
            f"[#555d66]{'!shell':<9}[/] [{WARN}]{shell}[/]",
            f"[#555d66]{'Watch':<9}[/] {watch}",
        ])

    # --- действия ---
    def action_clear_log(self) -> None:
        self._clear_log()

    def action_history_up(self) -> None:
        if self.history:
            self._hist_index = max(0, self._hist_index - 1)
            self.query_one("#cmd", Input).value = self.history[self._hist_index]

    def action_history_down(self) -> None:
        if self.history:
            self._hist_index = min(len(self.history), self._hist_index + 1)
            val = self.history[self._hist_index] if self._hist_index < len(self.history) else ""
            self.query_one("#cmd", Input).value = val


def run(enable_shell: bool = False) -> None:
    SysCheckTUI(enable_shell=enable_shell).run()
