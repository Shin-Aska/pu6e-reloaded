from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest


def test_user_configuration_uses_qt_standard_configuration_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pu6e_qt import configuration

    monkeypatch.setattr(
        configuration.QStandardPaths,
        "writableLocation",
        lambda location: str(tmp_path),
    )

    assert configuration.user_configuration_path() == (
        tmp_path / "pu6e-reloaded" / "config.ini"
    )


def test_legacy_configuration_migration_preserves_game_profiles_and_relative_paths(
    tmp_path: Path,
) -> None:
    from pu6e_qt.configuration import migrate_legacy_configuration

    project = tmp_path / "project"
    project.mkdir()
    legacy = project / "pu6e.conf"
    legacy.write_text(
        "[pu6e]\n"
        "gamedir = ultima\n"
        "gametype = fp\n"
        "width = 1280\n"
        "height = 720\n"
        "zoom = 1.5\n\n"
        "[game:fp]\n"
        "gamedir = ultima\n\n"
        "[game:md]\n"
        f"gamedir = {tmp_path / 'mars'}\n\n"
        "[game:se]\n"
        "gamedir = savage\n",
        encoding="utf-8",
    )
    destination = tmp_path / "user-config" / "pu6e-reloaded" / "config.ini"

    migrate_legacy_configuration(destination, legacy)

    saved = ConfigParser()
    saved.read(destination)
    assert saved.get("pu6e", "gametype") == "fp"
    assert saved.get("pu6e", "gamedir") == str(project / "ultima")
    assert saved.getint("pu6e", "width") == 1280
    assert saved.getfloat("pu6e", "zoom") == 1.5
    assert saved.get("game:fp", "gamedir") == str(project / "ultima")
    assert saved.get("game:md", "gamedir") == str(tmp_path / "mars")
    assert saved.get("game:se", "gamedir") == str(project / "savage")
    assert legacy.is_file()


def test_existing_user_configuration_is_never_overwritten(tmp_path: Path) -> None:
    from pu6e_qt.configuration import migrate_legacy_configuration

    legacy = tmp_path / "pu6e.conf"
    legacy.write_text("[pu6e]\ngametype = fp\n", encoding="utf-8")
    destination = tmp_path / "config.ini"
    existing = "[pu6e]\ngametype = se\n"
    destination.write_text(existing, encoding="utf-8")

    migrate_legacy_configuration(destination, legacy)

    assert destination.read_text(encoding="utf-8") == existing


def test_first_run_without_legacy_configuration_creates_no_file(tmp_path: Path) -> None:
    from pu6e_qt.configuration import migrate_legacy_configuration

    destination = tmp_path / "user-config" / "config.ini"

    migrate_legacy_configuration(destination, tmp_path / "pu6e.conf")

    assert not destination.exists()


def test_saving_first_game_creates_missing_user_configuration_directory(
    tmp_path: Path,
) -> None:
    from pu6e_qt.game_profiles import GameProfileStore

    destination = tmp_path / "user-config" / "pu6e-reloaded" / "config.ini"
    store = GameProfileStore(destination)
    game_directory = tmp_path / "ultima"

    store.set_directory("fp", game_directory)

    saved = ConfigParser()
    saved.read(destination)
    assert saved.get("game:fp", "gamedir") == str(game_directory)


def test_application_defaults_to_the_user_configuration_file() -> None:
    from pu6e_qt.application import _CONFIG_PATH
    from pu6e_qt.configuration import user_configuration_path

    assert _CONFIG_PATH == user_configuration_path()
