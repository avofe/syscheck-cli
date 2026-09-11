"""Главный entry point для syscheck CLI."""
import json
import sys
import typer
from rich.console import Console

# Windows console encoding fix (support emoji/unicode)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from syscheck import __version__
from syscheck.plugin import get_plugins

app = typer.Typer(
    name="syscheck",
    help="syscheck — CLI-утилита диагностики системы",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"syscheck v{__version__}")
        raise typer.Exit()


@app.callback()
def main_cb(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Показать версию",
    ),
):
    """syscheck — диагностика системы из терминала.

    Запуск без аргументов открывает интерактивную оболочку (TUI).
    syscheck <команда> — одиночная проверка. --help по командам.
    """


# Импорт и регистрация команд
from syscheck.commands.cpu import cpu_cmd
from syscheck.commands.ram import ram_cmd
from syscheck.commands.disk import disk_cmd
from syscheck.commands.net import net_cmd
from syscheck.commands.proc import proc_cmd
from syscheck.commands.temp import temp_cmd
from syscheck.commands.sys import sys_cmd
from syscheck.commands.watch import watch_cmd
from syscheck.commands.gpu import gpu_cmd
from syscheck.commands.battery import battery_cmd

app.command("cpu")(cpu_cmd)
app.command("ram")(ram_cmd)
app.command("disk")(disk_cmd)
app.command("net")(net_cmd)
app.command("proc")(proc_cmd)
app.command("temp")(temp_cmd)
app.command("sys")(sys_cmd)
app.command("watch")(watch_cmd)
app.command("gpu")(gpu_cmd)
app.command("battery")(battery_cmd)


def _all_data() -> dict:
    """Все метрики одним JSON-объектом (для `all --json`)."""
    from syscheck import providers

    return {
        "cpu": providers.cpu_info(),
        "ram": providers.ram_info(),
        "disk": providers.disk_info(),
        "net": providers.net_info(),
        "net_rates": providers.network_speeds(),
        "temp": providers.temperatures(),
        "gpu": providers.gpu_info(),
        "battery": providers.battery_info(),
        "sys": providers.system_info(),
    }


@app.command("all")
def all_cmd(
    output_json: bool = typer.Option(False, "--json", "-j", help="Вывод в JSON"),
):
    """Показать все метрики системы."""
    if output_json:
        console.print_json(json.dumps(_all_data(), indent=2, default=str))
        return

    from syscheck.commands.cpu import show_cpu
    from syscheck.commands.ram import show_ram
    from syscheck.commands.disk import show_disk
    from syscheck.commands.net import show_net
    from syscheck.commands.temp import show_temp
    from syscheck.commands.sys import show_sys
    from syscheck.commands.gpu import show_gpu
    from syscheck.commands.battery import show_battery

    console.rule("syscheck — Полная диагностика")
    console.print()
    show_cpu()
    console.print()
    show_ram()
    console.print()
    show_gpu()
    console.print()
    show_disk()
    console.print()
    show_net()
    console.print()
    show_temp()
    console.print()
    show_battery()
    console.print()
    show_sys()


@app.command("plugins")
def plugins_cmd(
    list_plugins: bool = typer.Option(False, "--list", "-l", help="Список плагинов"),
    plugin_name: str = typer.Option(None, "--run", "-r", help="Запустить плагин"),
):
    """Управление плагинами."""
    plugins = get_plugins()

    if not plugins:
        console.print("[dim]Плагины не найдены. Добавьте .py файлы в syscheck/plugins/[/]")
        return

    if list_plugins or (not plugin_name):
        from rich.table import Table
        table = Table(title="Доступные плагины", show_header=True, header_style="bold cyan")
        table.add_column("Имя", style="green")
        table.add_column("Описание")
        table.add_column("Версия", style="dim")
        for name, p in plugins.items():
            table.add_row(name, p.description, p.version)
        console.print(table)
        return

    if plugin_name:
        plugin = plugins.get(plugin_name)
        if plugin:
            plugin.execute()
        else:
            console.print(f"[red]Плагин '{plugin_name}' не найден.[/]")
            console.print(f"Доступные: {', '.join(plugins.keys())}")


def main():
    """Точка входа: без аргументов → TUI, с аргументами → CLI."""
    enable_shell = False
    args = list(sys.argv[1:])
    if "--enable-shell" in args:
        enable_shell = True
        args.remove("--enable-shell")
        sys.argv = [sys.argv[0]] + args
    if len(args) <= 0:
        from syscheck.tui import run as run_tui
        run_tui(enable_shell=enable_shell)
    else:
        app()
