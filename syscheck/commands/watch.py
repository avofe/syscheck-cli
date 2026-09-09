"""Команда syscheck watch — live-мониторинг (дашборд)."""
import time

import typer
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from syscheck import providers
from syscheck.utils import console, bytes_to_human, seconds_to_human, make_bar, get_color_for_percent


def _cpu_panel() -> Panel:
    d = providers.cpu_info()
    colour = get_color_for_percent(d["percent"])
    lines = [f"overall  [{colour}]{d['percent']:5.1f}%[/] {make_bar(d['percent'], 18)}"]
    if d["freq_current"]:
        lines.append(f"freq     [cyan]{d['freq_current']:.0f} MHz[/]")
    parts = " ".join(f"[{get_color_for_percent(p)}]{p:3.0f}[/]" for p in (d["per_cpu"] or []))
    lines.append(f"cores    {parts}")
    return Panel("\n".join(lines), title="cpu", border_style="dim")


def _ram_panel() -> Panel:
    d = providers.ram_info()
    colour = get_color_for_percent(d["percent"])
    lines = [f"usage    [{colour}]{d['percent']:5.1f}%[/] {make_bar(d['percent'], 18)}"]
    lines.append(f"used     [cyan]{bytes_to_human(d['used'])}[/] / {bytes_to_human(d['total'])}")
    if d["swap_total"] > 0:
        lines.append(f"swap     {d['swap_percent']}%")
    return Panel("\n".join(lines), title="ram", border_style="dim")


def _disk_panel() -> Panel:
    d = providers.disk_info()
    lines = []
    for disk in d["disks"]:
        colour = get_color_for_percent(disk["percent"])
        lines.append(
            f"{disk['device'].ljust(6)} [{colour}]{disk['percent']:4.1f}%[/] {make_bar(disk['percent'], 12)} "
            f"{bytes_to_human(disk['free'])} free"
        )
    return Panel("\n".join(lines) or "[dim]нет дисков[/]", title="disk", border_style="dim")


def _net_panel() -> Panel:
    d = providers.net_info()
    lines = []
    if d["io"]:
        lines.append(f"sent  [magenta]{bytes_to_human(d['io']['bytes_sent'])}[/]")
        lines.append(f"recv  [magenta]{bytes_to_human(d['io']['bytes_recv'])}[/]")
    for i in d["interfaces"]:
        if i["up"] and i["ipv4"]:
            lines.append(f"[green]{i['name']}[/]  {i['ipv4'][0]}")
    return Panel("\n".join(lines), title="network", border_style="dim")


def _proc_panel() -> Panel:
    d = providers.processes(sort_by="cpu", limit=8)
    lines = [f"{'pid':<7}{'process':<22}{'cpu':>6}{'ram':>6}"]
    for p in d:
        cpu = p.get("cpu_percent") or 0
        ram = p.get("memory_percent") or 0
        lines.append(
            f"{p['pid']:<7}{(p['name'] or '?')[:20]:<22}"
            f"{get_color_for_percent(cpu)}{cpu:5.1f}%[/]"
            f"{get_color_for_percent(ram)}{ram:5.1f}%[/]"
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


def watch_cmd(
    interval: int = typer.Option(2, "--interval", "-i", help="Интервал обновления (сек)"),
):
    """Live-мониторинг системы (Dashboard)."""
    console.print("[dim]syscheck watch — ctrl+c для выхода[/]")

    layout = _build_layout()
    header = Panel(
        Text("syscheck watch", justify="center", style="bold"),
        style="dim",
    )
    try:
        with Live(layout, refresh_per_second=1, screen=True):
            providers.cpu_info()
            for _ in range(1200):
                layout["header"].update(header)
                layout["cpu"].update(_cpu_panel())
                layout["ram"].update(_ram_panel())
                layout["disk"].update(_disk_panel())
                layout["net"].update(_net_panel())
                layout["procs"].update(_proc_panel())
                s = providers.system_info()
                lines = [
                    f"uptime   {seconds_to_human(s['uptime_seconds'])}",
                    f"node     {s['node']}",
                    f"procs    {len(providers.processes(sort_by='cpu', limit=1000))}",
                ]
                layout["sys_info"].update(Panel("\n".join(lines), title="system", border_style="dim"))
                time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[dim]мониторинг остановлен.[/]")
