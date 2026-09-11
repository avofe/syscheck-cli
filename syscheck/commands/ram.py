"""Команда syscheck ram — диагностика оперативной памяти."""
import json

import typer

from syscheck import config, providers
from syscheck.utils import (
    console, make_bar, print_value, print_header, get_color_for_percent, bytes_to_human,
)


def show_ram() -> None:
    data = providers.ram_info()
    warn, crit = config.thresholds("mem")

    print_header("ram")

    colour = get_color_for_percent(data["percent"], "mem")
    console.print(
        f"usage       [{colour}]{data['percent']}%[/] {make_bar(data['percent'], name='mem')}"
    )
    print_value("used", f"{bytes_to_human(data['used'])} / {bytes_to_human(data['total'])}")
    print_value("free", bytes_to_human(data["available"]))
    if data["swap_total"] > 0:
        print_value("swap", f"{data['swap_percent']}% ({bytes_to_human(data['swap_total'])})")

    if data["top_procs"]:
        console.print()
        print_header("top by ram")
        for p in data["top_procs"]:
            pct = p["memory_percent"] or 0
            pc = get_color_for_percent(pct, "mem")
            console.print(
                f"  {p['pid']:<8} {(p['name'] or '?')[:28]:<28} [{pc}]{pct:5.1f}%[/]"
            )

    if data["percent"] >= crit:
        console.print("  [red][!] память почти исчерпана[/]")
    elif data["percent"] >= warn:
        console.print("  [yellow][!] много памяти используется[/]")


def ram_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Диагностика оперативной памяти."""
    if output_json:
        console.print_json(json.dumps(providers.ram_info(), indent=2))
    else:
        show_ram()
