"""Команда syscheck disk — диагностика дисков."""
import json

import typer

from syscheck import providers
from syscheck.utils import (
    console, make_bar, print_value, print_header, get_color_for_percent, bytes_to_human,
    print_error, print_warning,
)


def show_disk() -> None:
    data = providers.disk_info()

    print_header("disks")

    if not data["disks"]:
        console.print("[dim]диски не найдены[/]")
        return

    for d in data["disks"]:
        colour = get_color_for_percent(d["percent"])
        console.print(
            f"{d['device'].ljust(8)} [{colour}]{d['percent']:4.1f}%[/] {make_bar(d['percent'])}  "
            f"{bytes_to_human(d['used'])} / {bytes_to_human(d['total'])}  "
            f"(free {bytes_to_human(d['free'])})"
        )

    io = data["io"]
    if io:
        console.print()
        print_header("io")
        print_value("read", bytes_to_human(io.read_bytes))
        print_value("write", bytes_to_human(io.write_bytes))

    for d in data["disks"]:
        if d["percent"] > 95:
            print_error(f"{d['device']}: критически мало места!")
        elif d["percent"] > 85:
            print_warning(f"{d['device']}: мало свободного места")


def disk_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Диагностика дисков (место, состояние, I/O)."""
    if output_json:
        out = []
        for d in providers.disk_info()["disks"]:
            out.append({
                "device": d["device"],
                "mountpoint": d["mountpoint"],
                "total": d["total"],
                "used": d["used"],
                "free": d["free"],
                "percent": d["percent"],
            })
        console.print_json(json.dumps(out, indent=2))
    else:
        show_disk()
