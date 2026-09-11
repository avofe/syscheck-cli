"""Команда syscheck gpu — информация о видеокарте."""
import json

import typer

from syscheck import providers
from syscheck.utils import console, print_header, print_value


def show_gpu() -> None:
    g = providers.gpu_info()

    print_header("gpu")

    if not g.get("name"):
        console.print("[dim]gpu-информация не обнаружена[/]")
        return

    print_value("gpu", g["name"])
    if g.get("vram_gb"):
        print_value("vram", f"{g['vram_gb']:.1f} GB")
    if g.get("util") is not None:
        print_value("util", f"{g['util']:.0f}%")
    if g.get("temp") is not None:
        print_value("temp", f"{g['temp']:.0f}°C")
    if g.get("util") is None and g.get("temp") is None:
        console.print("[dim]utilization/temp не отдаются этим драйвером[/]")


def gpu_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Информация о видеокарте (имя, VRAM)."""
    if output_json:
        console.print_json(json.dumps(providers.gpu_info(), indent=2))
    else:
        show_gpu()