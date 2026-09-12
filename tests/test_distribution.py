from __future__ import annotations

from configparser import ConfigParser
from fnmatch import fnmatchcase
from pathlib import Path
import tomllib
from typing import Final
from xml.etree import ElementTree

import pytest


_PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]


def test_packaging_dependency_group_contains_pyinstaller() -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        project = tomllib.load(source)

    packaging_dependencies = project["dependency-groups"]["packaging"]

    assert any(dependency.startswith("pyinstaller>=") for dependency in packaging_dependencies)


def test_source_distribution_discovers_game_and_ui_subpackages() -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        project = tomllib.load(source)

    setuptools = project["tool"]["setuptools"]
    includes = setuptools["packages"]["find"]["include"]
    source_root = _PROJECT_ROOT / "src"
    packages = {
        ".".join(path.parent.relative_to(source_root).parts)
        for root in ("game", "ui")
        for path in (source_root / root).rglob("__init__.py")
    }

    assert {"game.models", "game.format", "game.services", "ui.rendering"} <= packages
    assert all(any(fnmatchcase(package, pattern) for pattern in includes) for package in packages)
    assert includes == ["game", "game.*", "ui", "ui.*"]
    assert not any(fnmatchcase("U6", pattern) for pattern in includes)
    assert not any(fnmatchcase("tests", pattern) for pattern in includes)
    assert setuptools["py-modules"] == ["pu6e"]
    assert setuptools["package-dir"] == {"": "src"}
    assert setuptools["packages"]["find"]["where"] == ["src"]
    assert (source_root / "pu6e.py").is_file()


@pytest.mark.parametrize("retired_package", ("pu6e_core", "pu6e_qt"))
def test_retired_source_packages_cannot_be_packaged_or_reintroduced(
    retired_package: str,
) -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        project = tomllib.load(source)

    includes = project["tool"]["setuptools"]["packages"]["find"]["include"]

    assert not (_PROJECT_ROOT / retired_package / "__init__.py").exists()
    assert not (_PROJECT_ROOT / "src" / retired_package / "__init__.py").exists()
    assert not any(
        fnmatchcase(retired_package, pattern)
        or fnmatchcase(f"{retired_package}.retired", pattern)
        for pattern in includes
    )


@pytest.mark.parametrize("build_script", ("build-linux.sh", "windows.spec"))
def test_packaged_applications_include_dynamic_opengl_platform_backends(build_script: str) -> None:
    arguments = (_PROJECT_ROOT / "packaging" / build_script).read_text(encoding="utf-8")

    assert "--collect-submodules" in arguments or "collect_submodules(" in arguments
    assert "OpenGL.platform" in arguments


@pytest.mark.parametrize("build_script", ("build-linux.sh", "windows.spec"))
def test_packaged_applications_include_game_and_renderer_subpackages(build_script: str) -> None:
    arguments = (_PROJECT_ROOT / "packaging" / build_script).read_text(encoding="utf-8")

    assert "game" in arguments
    assert "ui.rendering" in arguments


def test_windows_package_includes_the_runtime_opengl_plugin() -> None:
    specification = (_PROJECT_ROOT / "packaging" / "windows.spec").read_text(encoding="utf-8")

    assert '"ui.runtime.windows.opengl"' in specification


@pytest.mark.parametrize(
    ("build_script", "hidden_import"),
    (("build-linux.sh", "--hidden-import OpenGL.GL"), ("windows.spec", '"OpenGL.GL"')),
)
def test_packaged_applications_include_dynamically_imported_gl_bindings(
    build_script: str, hidden_import: str
) -> None:
    arguments = (_PROJECT_ROOT / "packaging" / build_script).read_text(encoding="utf-8")

    assert hidden_import in arguments


def test_linux_release_smoke_test_covers_egl_backend() -> None:
    workflow = (_PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "PYOPENGL_PLATFORM: egl" in workflow


def test_linux_desktop_entry_launches_the_packaged_application() -> None:
    desktop_entry = ConfigParser(interpolation=None)

    loaded = desktop_entry.read(
        _PROJECT_ROOT / "packaging" / "pu6e-reloaded.desktop",
        encoding="utf-8",
    )

    assert loaded
    assert desktop_entry["Desktop Entry"]["Type"] == "Application"
    assert desktop_entry["Desktop Entry"]["Exec"] == "pu6e-reloaded"
    assert desktop_entry["Desktop Entry"]["Icon"] == "pu6e-reloaded"


def test_linux_desktop_icon_is_valid_scalable_vector_artwork() -> None:
    icon = ElementTree.parse(_PROJECT_ROOT / "packaging" / "pu6e-reloaded.svg")

    assert icon.getroot().tag == "{http://www.w3.org/2000/svg}svg"
    assert icon.getroot().attrib["viewBox"] == "0 0 256 256"
