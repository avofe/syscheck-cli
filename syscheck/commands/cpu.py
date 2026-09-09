"""Команда syscheck cpu — диагностика процессора."""
import json

import typer

from syscheck import providers
from syscheck.utils import console, make_bar, print_value, print_header, get_color_for_percent


def show_cpu() -> None:
    data = providers.cpu_info()
    per_cpu = data["per_cpu"] or []

    print_header("cpu")

    colour = get_color_for_percent(data["percent"])
    console.print(
        f"load        [{colour}]{data['percent']}%[/] {make_bar(data['percent'])}"
    )
    print_value("cores", f"{data['count_physical'] or '?'} physical / {data['count_logical']} logical")
    if data["freq_current"]:
        freq = f"{data['freq_current']:.0f} MHz"
        if data["freq_max"]:
            freq += f" (max {data['freq_max']:.0f} MHz)"
        print_value("freq", freq)
    if per_cpu:
        parts = "  ".join(
            f"[{get_color_for_percent(p)}]{i}: {p:.0f}[/]" for i, p in enumerate(per_cpu)
        )
        console.print(f"per-core    {parts}")

    if data["percent"] >= 90:
        console.print("  [red][!] CPU сильно нагружен[/]")
    elif data["percent"] >= 75:
        console.print("  [yellow][!] CPU заметно нагружен[/]")


def cpu_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Диагностика процессора (нагрузка, ядра, частота)."""
    if output_json:
        console.print_json(json.dumps(providers.cpu_info(), indent=2))
    else:
        show_cpu()
