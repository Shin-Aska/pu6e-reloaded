from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Final

import pytest

_PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
_LEGACY_ARTIFACTS: Final = (
    "Makefile",
    "Makefile.def",
    "Pseudohash.py",
    "mapedit_wxgl.py",
    "setup-exe.py",
    "fastgl",
    "lzw",
    "u6decode",
    "U6",
    "mapedit_gl.py",
    "fastgl.py",
    "U6/BookEdit.py",
    "U6/ChunkEdit.py",
    "U6/GoTo.py",
    "U6/HexCtrl.py",
    "U6/ObjEdit.py",
    "U6/StackEdit.py",
    "U6/TileEdit.py",
    "U6/TileEditGL.py",
    "U6/wxtile.py",
    "U6/wxutil.py",
)


@pytest.mark.parametrize("relative_path", _LEGACY_ARTIFACTS)
def test_obsolete_legacy_artifact_is_not_shipped(relative_path: str) -> None:
    assert not (_PROJECT_ROOT / relative_path).exists()


def test_game_engine_contains_no_presentation_or_legacy_imports() -> None:
    forbidden_import = re.compile(
        r"^\s*(?:from|import)\s+(?:wx|PySide6|OpenGL|pu6e_qt|U6|mapedit_gl|fastgl)(?:[.\s]|$)",
        re.MULTILINE,
    )
    offenders = tuple(
        source.relative_to(_PROJECT_ROOT)
        for source in (_PROJECT_ROOT / "pu6e_core").rglob("*.py")
        if forbidden_import.search(source.read_text(encoding="utf-8"))
    )

    assert offenders == ()


def test_package_declares_only_active_top_level_modules() -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        configuration = tomllib.load(source)

    assert configuration["tool"]["setuptools"]["py-modules"] == [
        "pu6e",
    ]


def test_game_engine_utilities_exclude_wx_only_helpers() -> None:
    from pu6e_core.models import coordinates

    assert not hasattr(coordinates, "index_ref")
    assert not hasattr(coordinates, "Bunch")
