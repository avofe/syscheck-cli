"""Тесты: однострочные установщики (без Python) и их пути в README."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL_PS1 = ROOT / "install.ps1"
INSTALL_SH = ROOT / "install.sh"
README = ROOT / "README.md"
PACKAGING = ROOT / "packaging"


def test_install_scripts_exist():
    assert INSTALL_PS1.is_file(), "нужен install.ps1 в корне репо"
    assert INSTALL_SH.is_file(), "нужен install.sh в корне репо"


def test_install_ps1_downloads_windows_asset():
    text = INSTALL_PS1.read_text(encoding="utf-8")
    assert "syscheck-windows-x86_64.exe" in text
    assert "releases/latest/download/" in text
    assert "LOCALAPPDATA" in text
    assert "syscheck" in text.lower()


def test_install_sh_has_all_assets_and_no_python_requirement():
    text = INSTALL_SH.read_text(encoding="utf-8")
    for asset in ("syscheck-linux-x86_64", "syscheck-macos-arm64"):
        assert asset in text
    assert "releases/latest/download/" in text
    assert "pipx" not in text and "pip install" not in text


def test_readme_uses_root_install_scripts():
    text = README.read_text(encoding="utf-8")
    assert "main/install.ps1" in text
    assert "main/install.sh" in text
    assert "main/scripts/install" not in text


def test_release_readme_exists():
    assert (PACKAGING / "release-README.txt").is_file()