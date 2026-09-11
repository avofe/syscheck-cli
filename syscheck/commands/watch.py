"""Команда syscheck watch — live-мониторинг (дашборд)."""
import json
import time
from collections import deque
from typing import Dict, Optional

import typer
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from syscheck import config, providers
from syscheck.utils import (
    console, bytes_to_human, seconds_to_human, make_bar, get_color_for_percent,
    sparkline, supports_block_chars,
)

_mem_hist: deque = deque(maxlen=60)
_SPARK_ASCII = not supports_block_chars()


def _spark(values, width: int) -> str:
    return sparkline(values, width, ascii=_SPARK_ASCII)


def _collect() -> Dict:
    """Один проход данных за тик (неблокирующий CPU по дельтам)."""
    delta = providers.cpu_delta()
    base = providers.cpu_info(interval=None)
    cpu = dict(base)
    if delta is not None:
        cpu["percent"], cpu["per_cpu"] = delta
    ram = providers.ram_info()
    _mem_hist.append(ram["percent"])
    return {
        "cpu": cpu,
        "ram": ram,
        "disk": providers.disk_info(),
        "net": providers.net_info(),
        "net_rates": providers.network_speeds(),
        "io": providers.disk_io_speeds(),
        "procs": providers.processes(sort_by="cpu", limit=8),
        "proc_count": providers.process_count(),
        "sys": providers.system_info(),
        "cpu_hist": providers.cpu_history(),
        "mem_hist": list(_mem_hist),
        "net_hist": providers.net_history(),
        "disk_hist": providers.disk_history(),
    }


def _cpu_panel(d: Dict, hist: list) -> Panel:
    colour = get_color_for_percent(d["percent"], "cpu")
    lines = [
        f"overall  [{colour}]{d['percent']:5.1f}%[/] {make_bar(d['percent'], 18, 'cpu')}",
        f"trend    [dim]{_spark(hist, 22)}[/]",
    ]
    if d["freq_current"]:
        lines.append(f"freq     [cyan]{d['freq_current']:.0f} MHz[/]")
    parts = " ".join(f"[{get_color_for_percent(p, 'cpu')}]{p:3.0f}[/]" for p in (d["per_cpu"] or []))
    lines.append(f"cores    {parts}")
    return Panel("\n".join(lines), title="cpu", border_style="dim")


def _ram_panel(d: Dict, hist: list) -> Panel:
    colour = get_color_for_percent(d["percent"], "mem")
    lines = [
        f"usage    [{colour}]{d['percent']:5.1f}%[/] {make_bar(d['percent'], 18, 'mem')}",
        f"trend    [dim]{_spark(hist, 22)}[/]",
    ]
    lines.append(f"used     [cyan]{bytes_to_human(d['used'])}[/] / {bytes_to_human(d['total'])}")
    if d["swap_total"] > 0:
        lines.append(f"swap     {d['swap_percent']}%")
    return Panel("\n".join(lines), title="ram", border_style="dim")


def _disk_panel(d: Dict, io: Dict, hist: dict) -> Panel:
    lines = []
    for disk in d["disks"]:
        colour = get_color_for_percent(disk["percent"], "disk")
        lines.append(
            f"{disk['device'].ljust(6)} [{colour}]{disk['percent']:4.1f}%[/] "
            f"{make_bar(disk['percent'], 12, 'disk')} "
            f"{bytes_to_human(disk['free'])} free"
        )
    if io:
        lines.append(
            f"read     [cyan]{bytes_to_human(io['read'])}/s[/]  "
            f"[dim]{_spark(hist.get('read'), 12)}[/]"
        )
        lines.append(
            f"write    [cyan]{bytes_to_human(io['write'])}/s[/]  "
            f"[dim]{_spark(hist.get('write'), 12)}[/]"
        )
    return Panel("\n".join(lines) or "[dim]нет дисков[/]", title="disk", border_style="dim")


def _net_panel(d: Dict, rates: Dict, hist: dict) -> Panel:
    lines = []
    if rates:
        lines.append(
            f"down     [cyan]{bytes_to_human(rates['down'])}/s[/]  "
            f"[dim]{_spark(hist.get('down'), 12)}[/]"
        )
        lines.append(
            f"up       [cyan]{bytes_to_human(rates['up'])}/s[/]  "
            f"[dim]{_spark(hist.get('up'), 12)}[/]"
        )
    if d["io"]:
        lines.append(f"sent     [magenta]{bytes_to_human(d['io']['bytes_sent'])}[/]")
        lines.append(f"recv     [magenta]{bytes_to_human(d['io']['bytes_recv'])}[/]")
    for i in d["interfaces"]:
        if i["up"] and i["ipv4"]:
            lines.append(f"[green]{i['name']}[/]  {i['ipv4'][0]}")
    return Panel("\n".join(lines), title="network", border_style="dim")


def _proc_panel(procs: list) -> Panel:
    lines = [f"{'pid':<7}{'process':<22}{'cpu':>6}{'ram':>6}"]
    for p in procs:
        cpu = p.get("cpu_percent") or 0
        ram = p.get("memory_percent") or 0
        lines.append(
            f"{p['pid']:<7}{(p['name'] or '?')[:20]:<22}"
            f"[{get_color_for_percent(cpu, 'cpu')}]{cpu:5.1f}%[/]"
            f"[{get_color_for_percent(ram, 'mem')}]{ram:5.1f}%[/]"
        )
    return Panel("\n".join(lines), title="processes", border_style="dim")


def _build_layout() -> Layout:
    layout = Layout()
    layout.split_column(Layout(name="header", size=1), Layout(name="body"))
    layout["body"].split_column(Layout(name="top", ratio=1), Layout(name="bottom", ratio=1))
    layout["top"].split_row(Layout(name="cpu", ratio=2), Layout(name="ram", ratio=1))
    layout["bottom"].split_row(
        Layout(name="disk", ratio=1), Layout(name="net", ratio=1),
        Layout(name="procs", ratio=2), Layout(name="sys_info", ratio=1),
    )
    return layout


def _run_dashboard(interval: int) -> None:
    layout = _build_layout()
    header = Panel(Text("syscheck watch", justify="center", style="bold"), style="dim")
    with Live(layout, refresh_per_second=1, screen=True):
        while True:
            layout["header"].update(header)
            data = _collect()
            layout["cpu"].update(_cpu_panel(data["cpu"], data["cpu_hist"]))
            layout["ram"].update(_ram_panel(data["ram"], data["mem_hist"]))
            layout["disk"].update(_disk_panel(data["disk"], data["io"], data["disk_hist"]))
            layout["net"].update(_net_panel(data["net"], data["net_rates"], data["net_hist"]))
            layout["procs"].update(_proc_panel(data["procs"]))
            s = data["sys"]
            lines = [
                f"uptime   {seconds_to_human(s['uptime_seconds'])}",
                f"node     {s['node']}",
                f"procs    {data['proc_count']}",
            ]
            layout["sys_info"].update(Panel("\n".join(lines), title="system", border_style="dim"))
            time.sleep(interval)


def _run_json(interval: int, iterations: Optional[int]) -> None:
    """JSON-режим: одна JSON-строка на тик (для скриптов/пайпов)."""
    count = 0
    while iterations is None or count < iterations:
        data = _collect()
        console_print_json(data)
        count += 1
        time.sleep(interval)


def console_print_json(data: Dict) -> None:
    console.print_json(json.dumps(data, indent=2, default=str))


def watch_cmd(
    interval: Optional[int] = typer.Option(
        None, "--interval", "-i", help="Интервал обновления в секундах (по умолчанию из конфига)"
    ),
    iterations: Optional[int] = typer.Option(
        None, "--iterations", help="Количество итераций (по умолчанию — без лимита)"
    ),
    output_json: bool = typer.Option(False, "--json", "-j", help="Одна JSON-строка на тик"),
):
    """Live-мониторинг системы (Dashboard)."""
    if interval is None:
        interval = config.watch_interval()
    if output_json:
        try:
            _run_json(interval, iterations)
        except KeyboardInterrupt:
            pass
        return
    console.print("[dim]syscheck watch — ctrl+c для выхода[/]")
    try:
        _run_dashboard(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]мониторинг остановлен.[/]")