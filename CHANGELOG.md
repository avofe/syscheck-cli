# Changelog

Все заметные изменения в `syscheck` документируются здесь.
Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Версионирование: [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

(плановое)

## [0.5.0] — 2026-09-11

### Честность и удобство (Волна 1)

- `!shell` теперь реально работает: диспетчеризация `!`-команд в TUI
  (раньше команда была определена, но никогда не вызывалась)
- Исправлена опечатка в переменной окружения: `SYSSCHECK_CONFIG_DIR`
  → `SYSCHECK_CONFIG_DIR`
- `--json` говорит правду: `all --json` — всё одним JSON-объектом
  (раньше флаг игнорировался), `sys --json` включает summary,
  `watch --json` печатает один объект на тик
- `watch`: снят молчаливый лимит 1200 итераций, добавлен `--iterations N`
  (по умолчанию — бесконечно), убран блокирующий опрос CPU (0.3с)
- Новые CLI-команды `syscheck gpu` и `syscheck battery` (раньше
  существовали только внутри TUI)
- Первый экран TUI: CPU и PROCESSES видны по умолчанию; `0` — показать
  все панели (README обещало, кода не было)
- Сортировка процессов в одну клавишу `t` (CPU → RAM → имя)
- Конфиг-файл `~/.syscheck/config.toml`: интервал TUI и watch, ping-хост,
  видимые панели, пороги цветов/предупреждений (cpu/mem/disk). Пороги
  применяются и в TUI, и в CLI
- Исправлены мелочи: аннотация `disk_info`, кракозябры в справке cmdlang
- На Python 3.10 конфиг читается через `tomli` (в 3.11+ — встроенный `tomllib`)

## [0.4.0] — 2026-09-11

### Полнота продукта и доверие

- CI (GitHub Actions): тесты на Python 3.10–3.13, авто-сборка standalone-бинарей
  под Windows / Linux / macOS (arm64) и автопубликация на PyPI при создании тега
- Сборка exe: выключена UPX-упаковка — меньше ложных срабатываний антивирусов
- PyPI: полные метаданные (`project.urls`, `classifiers`, `keywords`, авторы),
  современный формат лицензии MIT
- README: бейджи CI/PyPI/license, секции SmartScreen / антивирус / Windows Terminal,
  английская версия для международных пользователей
- `SECURITY.md` и `CHANGELOG.md`
- Лицензия MIT

## [0.3.0] — 2026-09-11

### Распространение

- Пакет опубликован на PyPI под именем `syscheck-cli`
- Standalone-бинари на GitHub Releases
- `scripts/install.ps1` (Windows) и `scripts/install.sh` (macOS/Linux)
- `syscheck.spec` — PyInstaller onefile-сборка

## [0.2.0] — 2026-09-11

### TUI (новое)

- Интерактивный режим `syscheck` без аргументов: живой дашборд
  (CPU, MEMORY, GPU, STORAGE, NETWORK, BATTERY, PROCESSES)
- Палитра команд `Ctrl+P`, переключение панелей `1`–`5`, карточки процессов
- Команда `!shell` с подтверждением и audit-логом

## [0.1.0] — 2026-09-11

### Первый релиз

- Базовые команды `syscheck cpu|ram|disk|net|proc|temp|sys|all|watch`
- `--json` для машинного вывода