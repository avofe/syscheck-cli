# syscheck

[![CI](https://github.com/avofe/syscheck-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/avofe/syscheck-cli/actions)
[![PyPI version](https://img.shields.io/pypi/v/syscheck-cli.svg)](https://pypi.org/project/syscheck-cli/)
[![Python](https://img.shields.io/pypi/pyversions/syscheck-cli.svg)](https://pypi.org/project/syscheck-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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
twine upload dist/*.whl dist/*.tar.gz # только py-артефакты (exe не трогаем)
```

## Команды

| Команда | Описание |
|---------|----------|
| `syscheck cpu` | Нагрузка CPU, ядра, частота |
| `syscheck ram` | Оперативная память, топ процессов по RAM |
| `syscheck disk` | Диски: место, состояние, I/O |
| `syscheck net --ping 8.8.8.8` | Сеть: интерфейсы, трафик, пинг |
| `syscheck gpu` | Видеокарта: имя + VRAM (used/total); на NVIDIA — ещё util и temp через `nvidia-smi` |
| `syscheck battery` | Состояние батареи |
| `syscheck proc --sort cpu` | Топ процессов (cpu/ram) |
| `syscheck temp` | Температуры: psutil, на Windows — дополнительно ACPI-зоны через WMI |
| `syscheck sys` | ОС, uptime, hostname (+ summary) |
| `syscheck all` | Вся диагностика сразу |
| `syscheck watch` | Live-дашборд (обновление каждые N сек) |

Каждая команда поддерживает `--json` для машинного вывода.
`all --json` — всё одним объектом; `sys --json` включает summary;
`watch --json` печатает один JSON-объект на тик (для скриптов),
`watch --iterations N` останавливает мониторинг после N тиков
(по умолчанию работает без лимита).

## Интерактивный режим (TUI)

Запуск `syscheck` без аргументов открывает живой дашборд (в духе btop/WinMon),
который обновляется каждые 2 секунды:

```
CPU  MEMORY             PROCESSES
 [████░░░░] 45%  [P]      PID PROCESS...
 FREQ 3.4GHz ...  TOTAL 15.3 GB  ...
                        …
 STORAGE  NETWORK
 ─────────────────────────────────────
 ❯ ram
 v0.5.0 · 0-5 toggle panels · t sort · ctrl+p palette
```

- **7 панелей**: CPU, MEMORY, GPU, STORAGE, NETWORK, BATTERY, PROCESSES.
  По умолчанию видны **PROCESSES + CPU, MEMORY, STORAGE, NETWORK** —
  главный вопрос («кто ест процессор») видно сразу; GPU и BATTERY — по клавише.
- **Тренды**: в панелях CPU, MEMORY, STORAGE и NETWORK живёт история
  последних ~60 тиков (спарклайн ▁▂▃▄▅▆▇█) — видно, растёт нагрузка или падает.
- **Тогглы панелей**: введи цифру и Enter — `1` CPU, `2` GPU, `3` NETWORK,
  `4` BATTERY, `5` PROCESSES, `0` показать все сразу.
- **Палитра команд**: `Ctrl+P` — фильтруй и запускай команды, `↑↓` выбор, `Enter` запуск, `Esc` закрыть
- **Инпут внизу** — обычные команды как в CLI (`ram`, `proc`, `net 8.8.8.8` …)
- **Процессы**: стрелками выбирай строку, `Enter` — карточка процесса,
  `K` — kill (с подтверждением), `S` — suspend, `R` — restart,
  `t` — цикличная сортировка CPU → RAM → имя, `/` — поиск, `Esc` — назад
- Выход: `exit`, `ctrl+c` или `q`

Команды работают и в TUI, и как обычный CLI (см. таблицу выше).

## Конфигурация

Файл `~/.syscheck/config.toml` (пользовательский каталог можно переопределить
переменной `SYSCHECK_CONFIG_DIR`). Все ключи опциональны:

```toml
refresh_interval = 2.0     # интервал обновления TUI (сек)
watch_interval = 2         # интервал `syscheck watch` по умолчанию (сек)
ping_host = "8.8.8.8"      # хост для пинга по умолчанию
default_panels = ["cpu", "ram", "disk", "net", "procs"]  # видимые панели TUI

[thresholds]
[thresholds.cpu]
warn = 75                  # жёлтый цвет
crit = 90                  # красный цвет
[thresholds.mem]
warn = 85
crit = 90
[thresholds.disk]
warn = 85
crit = 95
```

Пороги в конфиге применяются и к цветам TUI, и к предупреждениям CLI.
`syscheck settings` в TUI показывает путь к конфигу и текущие значения.

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
- Состояние `!shell` хранится в `~/.syscheck/config.json`; остальные
  настройки — в `~/.syscheck/config.toml` (см. «Конфигурация»).

---

## Частые вопросы

### Windows SmartScreen «защитил ваш компьютер»
Стандартная реакция при запуске неподписанного `.exe` из интернета.
Нажми «Подробнее» → «Выполнить в любом случае». Это безопасно:
код полностью прозрачен на [GitHub](https://github.com/avofe/syscheck-cli).

### Антивирус ругается на exe
PyInstaller-бинари иногда дают ложные срабатывания антивирусов.
Решение: исключить `syscheck.exe` из сканирования, либо ставить
через PyPI (`pip install syscheck-cli`) — тогда антивирус не цепляет.

### Запускать в Windows Terminal, а не в cmd
Текстовый интерфейс (TUI) использует unicode и цвета, которые
в старом консоле Windows отображаются корректно только в **Windows Terminal**.
Windows Terminal уже предустановлен в Windows 10/11.

### Почему exe только для x64
Билд собирается на GitHub Actions с `windows-latest` (x86_64).
Для ARM64 Windows нет отдельного бинарника; можно запустить
через Python: `pip install syscheck-cli`.

---

## Разработчику

### Запуск из исходников

```bash
git clone https://github.com/avofe/syscheck-cli
cd syscheck-cli
pip install -e .[dev]       # dev включает pytest, build, twine, pyinstaller
pytest                       # запуск тестов
python -m syscheck           # TUI
python -m syscheck cpu       # CLI
```

### Тесты

```bash
pytest               # все тесты (30+)
pytest -v            # подробно
```

### Сборка exe

```bash
pip install pyinstaller>=6.0.0
python -m PyInstaller --clean --noconfirm syscheck.spec
# → dist\syscheck.exe (onefile, ~23 МБ)
```

### Публикация релиза

```bash
python -m build
twine upload dist/*.whl dist/*.tar.gz
```

Или просто создай тег — GitHub Actions соберёт exe и опубликует всё автоматом:

```bash
git tag v0.3.0
git push origin main --tags
```

(Потребуется секрет `PYPI_API_TOKEN` в настройках репозитория.)

---

## Лицензия

MIT

---

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

---

## English (for international users)

**syscheck** — a system diagnostics tool with a live TUI dashboard (btop/WinMon
style) and simple CLI commands. No GUI, no dependencies beyond the terminal.

### Quick start

```bash
pipx install syscheck-cli     # or: pip install syscheck-cli
syscheck                       # live dashboard
```

No Python? Get a standalone binary from
[GitHub Releases](https://github.com/avofe/syscheck-cli/releases):

```powershell
# Windows
powershell -ExecutionPolicy Bypass -c "irm https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.ps1 | iex"
```

```bash
# Linux / macOS
curl -sSL https://raw.githubusercontent.com/avofe/syscheck-cli/main/scripts/install.sh | bash
```

### Features

- **TUI dashboard**: CPU, MEMORY, GPU, STORAGE, NETWORK, BATTERY, PROCESSES panels,
  live updates every N seconds. Toggle panels with `0`–`5` + Enter (`0` shows all),
  cycle process sort with `t` (CPU → RAM → name), open the command
  palette with `Ctrl+P`, run any command from the input line.
- **CLI commands**: `syscheck cpu|ram|gpu|battery|disk|net|proc|temp|sys|all|watch`
  (each supports `--json`). GPU reports real utilization/temperature via
  `nvidia-smi` on NVIDIA (VRAM used/total); otherwise name + total VRAM via
  WMI. `temp` on Windows additionally probes ACPI thermal zones (WMI).
- **JSON for scripts**: `all --json` — everything in one object, `watch --json`
  — one JSON line per tick, `watch --iterations N` — bounded monitoring.
- **Live trends**: CPU/MEMORY/STORAGE/NETWORK panels keep ~60 ticks of
  history and render sparklines; `watch` shows the same in the CPU/RAM/NET/disk
  panels.
- **Config file**: `~/.syscheck/config.toml` (TOML) for refresh interval,
  color thresholds and default panels.
- **Process details**: browse the process table, `Enter` opens a detail card,
  sort with `t`, filter with `/`, kill with `K`.
- **Plugins**: drop a `.py` file into `syscheck/plugins/` to add commands.
- **`!shell`**: optional shell access from the TUI, disabled by default and
  audited (`~/.syscheck/shell_audit.log`).

### Development

```bash
git clone https://github.com/avofe/syscheck-cli
cd syscheck-cli
pip install -e .[dev]
pytest          # run the test suite
```

Build standalone binaries for Windows/Linux/macOS, publish to PyPI — all
automatically. Just tag a release and push:

```bash
git tag v0.4.0 && git push origin main --tags
```

### License

MIT