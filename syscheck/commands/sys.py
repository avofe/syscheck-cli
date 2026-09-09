"""Команда syscheck sys — информация о системе."""
import json

import typer

from syscheck import providers
from syscheck.utils import (
    console, print_header, print_value, seconds_to_human, get_color_for_percent, bytes_to_human,
)


def show_sys() -> None:
    data = providers.system_info()

    print_header("system")

    print_value("os", f"{data['os']} ({data['machine']})")
    print_value("hostname", data["node"])
    print_value("processor", data["processor"])
    print_value("uptime", f"{seconds_to_human(data['uptime_seconds'])} (since {data['boot_datetime']})")
    print_value("python", data["python"])
    if data["users"]:
        print_value("users", ", ".join(data["users"]))

    console.print()
    quick = providers.system_quick()
    print_header("summary")
    console.print(f"cpu         [{get_color_for_percent(quick['cpu_percent'])}]{quick['cpu_percent']}%[/]")
    console.print(f"ram         [{get_color_for_percent(quick['ram_percent'])}]{quick['ram_percent']}%[/]  (free {bytes_to_human(quick['ram_available'])})")
    if quick.get("main_percent") is not None:
        console.print(f"disk        [{get_color_for_percent(quick['main_percent'])}]{quick['main_percent']}%[/]  (free {bytes_to_human(quick['main_free'])})")
    if quick.get("net_sent") is not None:
        console.print(f"network     sent {bytes_to_human(quick['net_sent'])}  recv {bytes_to_human(quick['net_recv'])}")


def sys_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Информация о системе (ОС, uptime, hostname)."""
    if output_json:
        console.print_json(json.dumps(providers.system_info(), indent=2))
    else:
        show_sys()
