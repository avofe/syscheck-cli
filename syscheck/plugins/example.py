"""Пример плагина для syscheck.

Чтобы создать свой плагин:
1. Создай .py файл в папке syscheck/plugins/
2. Создай класс, наследующий от PluginBase
3. Реализуй метод execute()
4. Плагин автоматически подхватится при запуске syscheck

Пример:
    syscheck plugins --list     # покажет все плагины
    syscheck plugins --run example  # запустит этот плагин
"""
from syscheck.plugin import PluginBase, register_plugin
from syscheck.utils import console, print_value, print_ok


class ExamplePlugin(PluginBase):
    name = "example"
    description = "Пример плагина — показывает информацию о библиотеках"
    version = "0.1.0"

    def execute(self, **kwargs):
        import psutil
        from importlib.metadata import version as _pkg_version
        import typer

        console.print("[dim]dependencies[/]")
        print_value("psutil", psutil.__version__)
        print_value("rich", _pkg_version("rich"))
        print_value("typer", _pkg_version("typer"))

        console.print()
        print_ok("Создай свой плагин в syscheck/plugins/!")


# Автоматическая регистрация при импорте
register_plugin(ExamplePlugin())

