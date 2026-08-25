from __future__ import annotations

from pathlib import Path
import re
import tomllib
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


def test_game_engine_contains_no_wx_imports() -> None:
    wx_import = re.compile(r"^\s*(?:from|import)\s+wx(?:[.\s]|$)", re.MULTILINE)
    offenders = tuple(
        source.relative_to(_PROJECT_ROOT)
        for source in (_PROJECT_ROOT / "U6").glob("*.py")
        if wx_import.search(source.read_text(encoding="utf-8"))
    )

    assert offenders == ()


def test_package_declares_only_active_top_level_modules() -> None:
    with (_PROJECT_ROOT / "pyproject.toml").open("rb") as source:
        configuration = tomllib.load(source)

    assert configuration["tool"]["setuptools"]["py-modules"] == [
        "fastgl",
        "mapedit_gl",
        "pu6e",
    ]


def test_game_engine_utilities_exclude_wx_only_helpers() -> None:
    from U6 import util

    assert not hasattr(util, "index_ref")
    assert not hasattr(util, "Bunch")
