# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для standalone-бинаря syscheck.

Сборка:   python -m PyInstaller --clean syscheck.spec
Результат: dist/syscheck.exe (Windows) / dist/syscheck (Linux/macOS).
Это onefile-бинарь — не требует установленного Python.
"""

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

_textual_datas, _textual_binaries, _textual_hidden = collect_all("textual")

datas = _textual_datas + collect_data_files("pyperclip")
binaries = _textual_binaries
hiddenimports = _textual_hidden

hiddenimports += collect_submodules("syscheck")
hiddenimports += [
    "syscheck.cli",
    "syscheck.tui",
    "syscheck.screens",
    "syscheck.cmdlang",
    "syscheck.palette",
    "syscheck.providers",
    "syscheck.shellguard",
    "syscheck.utils",
    "syscheck.plugin",
]
hiddenimports += collect_submodules("syscheck.commands")
hiddenimports += collect_submodules("syscheck.plugins")

datas += [("syscheck/plugins", "syscheck/plugins")]

a = Analysis(
    ["syscheck/__main__.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="syscheck",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)