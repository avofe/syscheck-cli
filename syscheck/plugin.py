"""Система плагинов для syscheck."""
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, Optional, Any

from rich.console import Console

console = Console()

PLUGINS_DIR = Path(__file__).parent / "plugins"


class PluginBase:
    """Базовый класс для плагинов. Наследуй от этого для создания своих команд."""

    name: str = "unnamed"
    description: str = "No description"
    version: str = "0.1.0"

    def execute(self, **kwargs) -> Any:
        """Выполняет команду плагина. Переопредели в дочернем классе."""
        raise NotImplementedError


_registry: Dict[str, PluginBase] = {}


def register_plugin(plugin: PluginBase):
    """Регистрирует плагин в системе."""
    _registry[plugin.name] = plugin


def get_plugins() -> Dict[str, PluginBase]:
    """Возвращает все зарегистрированные плагины."""
    _load_plugins_from_dir()
    return dict(_registry)


def get_plugin(name: str) -> Optional[PluginBase]:
    """Возвращает плагин по имени."""
    plugins = get_plugins()
    return plugins.get(name)


def _load_plugins_from_dir():
    """Загружает все плагины из директории plugins/."""
    if not PLUGINS_DIR.exists():
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        return

    for py_file in PLUGINS_DIR.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        _load_module(py_file)


def _load_module(module_path: Path):
    """Загружает один модуль-плагин."""
    spec = importlib.util.spec_from_file_location(
        f"syscheck.plugins.{module_path.stem}",
        module_path,
    )
    if spec is None or spec.loader is None:
        return

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        console.print(f"[red]Plugin load error ({module_path.name}): {e}[/]")
        return

    # Ищем классы-наследники PluginBase
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, PluginBase)
            and attr is not PluginBase
        ):
            try:
                instance = attr()
                register_plugin(instance)
            except Exception as e:
                console.print(f"[red]Plugin init error ({attr_name}): {e}[/]")
