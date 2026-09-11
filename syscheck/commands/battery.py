"""Команда syscheck battery — состояние батареи."""
import json

import typer

from syscheck import providers
from syscheck.utils import console, print_header, print_value


def show_battery() -> None:
    b = providers.battery_info()

    print_header("battery")

    if not b:
        console.print("[dim]батарея не обнаружена[/]")
        return

    print_value("charge", f"{b['percent']}%")
    state = "charging/plugged" if b.get("plugged") else "discharging"
    print_value("state", state)
    if b.get("seconds_left"):
        print_value("remaining", f"{int(b['seconds_left'] / 60)}m")


def battery_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Состояние батареи (если есть)."""
    if output_json:
        console.print_json(json.dumps(providers.battery_info(), indent=2))
    else:
        show_battery()