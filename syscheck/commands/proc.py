"""Команда syscheck proc — топ процессов."""
import json

import typer

from syscheck import providers
from syscheck.utils import console, print_header, get_color_for_percent


def show_proc(sort_by: str = "cpu", limit: int = 15) -> None:
    data = providers.processes(sort_by=sort_by, limit=limit)

    print_header(f"processes by {sort_by}")

    for p in data:
        cpu = p.get("cpu_percent") or 0
        ram = p.get("memory_percent") or 0
        status = p.get("status", "?")
        console.print(
            f"  {p['pid']:<8} {(p['name'] or '?')[:28]:<28} "
            f"cpu[{get_color_for_percent(cpu)}]{cpu:5.1f}[/]  "
            f"ram[{get_color_for_percent(ram)}]{ram:5.1f}[/]  {status}"
        )


def proc_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
    sort_by: str = typer.Option("cpu", "--sort", "-s", help="Сортировка: cpu, ram, name"),
    limit: int = typer.Option(15, "--limit", "-n", help="Количество процессов"),
):
    """Топ процессов по CPU/RAM."""
    if output_json:
        console.print_json(json.dumps(providers.processes(sort_by=sort_by, limit=limit), indent=2))
    else:
        show_proc(sort_by, limit)
