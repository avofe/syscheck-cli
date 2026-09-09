"""Команда syscheck net — диагностика сети."""
import json

import typer

from syscheck import providers
from syscheck.utils import (
    console, print_value, print_header, bytes_to_human, print_ok, print_warning, print_error,
)


def show_net(ping_host: str = "8.8.8.8") -> None:
    data = providers.net_info()

    print_header("network")

    for i in data["interfaces"]:
        status = "[green]up[/]" if i["up"] else "[dim]down[/]"
        ip = ", ".join(i["ipv4"]) if i["ipv4"] else "[dim]N/A[/]"
        speed = f"{i['speed']} Mbps" if i["speed"] else "-"
        console.print(f"  {status}  {i['name'].ljust(28)} {ip.ljust(18)} {speed}")
        if i["mac"]:
            console.print(f"{'':2}      mac: {', '.join(i['mac'])}")

    io = data["io"]
    if io:
        console.print()
        print_value("sent", bytes_to_human(io["bytes_sent"]))
        print_value("recv", bytes_to_human(io["bytes_recv"]))
        print_value("packets", f"{io['packets_sent']} / {io['packets_recv']}")

    console.print()
    print_header(f"ping {ping_host}")
    result = providers.ping(ping_host)
    if result["success"]:
        if result["avg_ms"] is not None:
            print_ok(f"{result['host']}: {result['avg_ms']:.1f} ms "
                     f"(min {result['min_ms']:.1f}, max {result['max_ms']:.1f})")
        else:
            print_ok(f"{result['host']}: пинг прошёл (время не определено)")
        if result["lost"] > 0:
            print_warning(f"потеряно {result['lost']}/{result['total']} пакетов")
        if result["avg_ms"] and result["avg_ms"] > 100:
            print_warning("высокий пинг")
    else:
        print_error(f"{ping_host}: недоступен")


def net_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
    ping_host: str = typer.Option("8.8.8.8", "--ping", "-p", help="Хост для пинга"),
):
    """Диагностика сети (интерфейсы, трафик, пинг)."""
    if output_json:
        data = providers.net_info()
        data["ping"] = providers.ping(ping_host)
        console.print_json(json.dumps(data, indent=2))
    else:
        show_net(ping_host)
