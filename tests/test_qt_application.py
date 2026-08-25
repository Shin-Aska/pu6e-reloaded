from __future__ import annotations

from pathlib import Path

import pytest

from test_core import write_game_fixture


@pytest.mark.parametrize("game", ("fp", "md", "se"))
def test_application_initializes_every_supported_game_fixture(
    tmp_path: Path, game: str
) -> None:
    from pu6e_qt.application import initialize_editor
    from U6 import Config
    import mapedit_gl as renderer

    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, game)
    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {game_dir}\n"
        f"gametype = {game}\n"
        "width = 800\n"
        "height = 600\n"
        "zoom = 1.5\n"
    )

    controller = initialize_editor(config_path)

    assert controller is not None
    assert Config.gamedir == str(game_dir.resolve())
    assert Config.gametype == game
    assert controller.position == (0x134, 0x16C, 0)
    assert renderer.get_centered_coords() == (0x134, 0x16C, 0)
    assert renderer.screen_width == 800
    assert renderer.screen_height == 600
    assert renderer.scale_factor == 1.5


def test_application_rejects_missing_game_directory(tmp_path: Path) -> None:
    from pu6e_qt.application import GameDirectoryError, initialize_editor

    config_path = tmp_path / "pu6e.conf"
    config_path.write_text(
        "[pu6e]\n"
        f"gamedir = {tmp_path / 'missing'}\n"
        "gametype = fp\n"
        "width = 800\n"
        "height = 600\n"
        "zoom = 1\n"
    )

    with pytest.raises(GameDirectoryError):
        initialize_editor(config_path)


def test_application_rejects_missing_configuration_file(tmp_path: Path) -> None:
    from pu6e_qt.application import ConfigurationFileError, initialize_editor

    with pytest.raises(ConfigurationFileError):
        initialize_editor(tmp_path / "missing.conf")


def test_application_package_import_is_wx_free() -> None:
    import importlib
    import sys

    importlib.import_module("pu6e")
    importlib.import_module("pu6e_qt.application")

    assert "wx" not in sys.modules
    assert "mapedit_wxgl" not in sys.modules
