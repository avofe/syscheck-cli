# syscheck

CLI-утилита диагностики системы, как btop/htop, но с рабочими командами.
Минималистичный ASCII-вывод: без рамок и emoji, только суть.

## Установка

### Быстро (нужен Python 3.10+)

```bash
pipx install syscheck-cli        # или: pip install syscheck-cli
syscheck                          # живой дашборд
```

Без PyPI — прямо из GitHub:

```bash
pip install git+https://github.com/avofe/syscheck-cli
```

### Без Python (Windows): готовый .exe одной строкой

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.ps1 | iex"
```

Скрипт скачивает `syscheck-windows-x86_64.exe` с GitHub Releases, кладёт в
`%LOCALAPPDATA%\syscheck` и добавляет в PATH. Python на машине не нужен.

### Без Python (macOS/Linux)

```bash
curl -sSL https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.sh | bash
```

### Из исходников

```bash
pip install -e .        # запуск: python -m syscheck
```

### Сборка exe (без Python у пользователя)

```powershell
.\scripts\build_exe.ps1     # → dist\syscheck-windows-x86_64.exe
```

### Публикация на PyPI (для автора)

```bash
pip install -e .[dev]
python -m build                       # wheel + sdist в dist/
twine upload dist/*                   # нужен аккаунт на pypi.org, токен
```

## Команды

| Команда | Описание |
|---------|----------|
| `syscheck cpu` | Нагрузка CPU, ядра, частота |
| `syscheck ram` | Оперативная память, топ процессов по RAM |
| `syscheck disk` | Диски: место, состояние, I/O |
| `syscheck net --ping 8.8.8.8` | Сеть: интерфейсы, трафик, пинг |
| `syscheck proc --sort cpu` | Топ процессов (cpu/ram) |
| `syscheck temp` | Температуры (если поддерживается) |
| `syscheck sys` | ОС, uptime, hostname |
| `syscheck all` | Вся диагностика сразу |
| `syscheck watch` | Live-дашборд (обновление каждые N сек) |

Каждая команда поддерживает `--json` для машинного вывода.

## Интерактивный режим (TUI)

Запуск `syscheck` без аргументов открывает интерактивную оболочку:
живой дашборд сверху (обновляется каждые 2 с) и строка ввода:

```
> cpu          # нагрузка процессора
> ram          # память
> disk         # диски
> net 8.8.8.8  # сеть и пинг
> proc         # топ процессов
> temp         # температуры
> sys          # система
> all          # всё сразу
> help         # помощь
> clear        # очистить
> exit / ctrl+c # выйти
```

## Безопасность `!shell`

Команда `!shell <cmd>` выполняет произвольные команды ОС прямо из TUI.
По умолчанию она **ВЫКЛЮЧЕНА** и включается только явным флагом:

```bash
syscheck --enable-shell
```

- При первом включении показывается предупреждение — нужно набрать `yes`.
- На **каждую** команду требуется подтверждение (повторить команду или `confirm`).
- Каждое выполнение записывается в audit-лог:
  `~/.syscheck/shell_audit.log`.
- Настройки хранятся в `~/.syscheck/config.json`.

## Плагины

Свои команды добавляются через плагины:

1. Создай файл `syscheck/plugins/мой_плагин.py`
2. Наследуй класс `PluginBase` из `syscheck.plugin`
3. Реализуй `execute()`
4. Плагин подхватится автоматически

```python
from syscheck.plugin import PluginBase, register_plugin
from syscheck.utils import console, print_value

class MyPlugin(PluginBase):
    name = "mycmd"
    description = "Моя команда"
    version = "0.1.0"

    def execute(self, **kwargs):
        print_value("hello", "syscheck!")

register_plugin(MyPlugin())
```

Запуск: `syscheck plugins --list` и `syscheck plugins --run mycmd`

## Пример использования

```bash
syscheck sys          # общее состояние системы
syscheck watch        # живой дашборд
syscheck proc --sort ram   # кто ест память
```