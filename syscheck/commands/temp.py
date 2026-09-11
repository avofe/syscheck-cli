"""Команда syscheck temp — температура сенсоров."""
import json

import typer

from syscheck import providers
from syscheck.utils import console, print_header, print_value, print_warning, print_error


def show_temp() -> None:
    data = providers.temperatures()

    print_header("temperatures")

    if not data["available"]:
        console.print("[dim]температуры не поддерживаются на этой системе[/]")
        console.print("[dim](нет сенсоров через psutil и нет ACPI-зон на Windows)[/]")
        return

    printed = False
    for name, entries in data["temps"].items():
        for e in entries:
            current = e.current
            high = e.high
            critical = e.critical
            printed = True
            print_value(name, f"{current:.0f}°C")
            if high and current >= high:
                print_warning(f"{name}: выше нормы ({current}°C >= {high}°C)")
            if critical and current >= critical:
                print_error(f"{name}: критическая! ({current}°C >= {critical}°C)")
    if not printed:
        console.print("[dim]датчиков температуры нет[/]")


def temp_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Температура сенсоров (CPU, GPU, SSD)."""
    if output_json:
        data = providers.temperatures()
        out = {}
        for name, entries in data["temps"].items():
            out[name] = [
                {"current": e.current, "high": e.high, "critical": e.critical}
                for e in entries
            ]
        console.print_json(json.dumps(out, indent=2))
    else:
        show_temp()
