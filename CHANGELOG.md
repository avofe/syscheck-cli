# Changelog

Все заметные изменения в `syscheck` документируются здесь.
Формат: [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Версионирование: [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

(плановое)

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