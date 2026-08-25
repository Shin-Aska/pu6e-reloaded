from __future__ import annotations

from configparser import ConfigParser
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


@pytest.mark.parametrize("build_script", ("build-linux.sh", "build-windows.ps1"))
def test_packaged_applications_include_dynamic_opengl_platform_backends(build_script: str) -> None:
    arguments = (_PROJECT_ROOT / "packaging" / build_script).read_text(encoding="utf-8")

    assert "--collect-submodules" in arguments
    assert "OpenGL.platform" in arguments


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
