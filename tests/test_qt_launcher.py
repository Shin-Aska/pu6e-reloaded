from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from test_core import write_game_fixture
from U6 import Config


@pytest.fixture(scope="session")
def launcher_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("game", ("fp", "md", "se"))
def test_game_profiles_recognize_complete_installations(tmp_path: Path, game: str) -> None:
    from pu6e_qt.game_profiles import GameProfileStore

    game_directory = tmp_path / game
    write_game_fixture(game_directory, game, game)
    store = GameProfileStore(tmp_path / "pu6e.conf")

    store.set_directory(game, game_directory)

    profile = store.profile(game)
    assert profile.ready
    assert profile.directory == game_directory.resolve()
    assert profile.missing_files == ()


def test_game_profiles_reject_an_installation_for_a_different_game(tmp_path: Path) -> None:
    from pu6e_qt.game_profiles import GameProfileStore

    ultima_directory = tmp_path / "ultima"
    write_game_fixture(ultima_directory, "fp", "ultima")
    store = GameProfileStore(tmp_path / "pu6e.conf")

    store.set_directory("md", ultima_directory)

    profile = store.profile("md")
    assert not profile.ready
    assert "mdpal" in profile.missing_files
    assert "look.lzc" in profile.missing_files


def test_game_profiles_detect_missing_required_object_blocks(tmp_path: Path) -> None:
    from pu6e_qt.game_profiles import GameProfileStore

    game_directory = tmp_path / "incomplete"
    write_game_fixture(game_directory, "fp", "incomplete")
    (game_directory / "savegame" / "objblkhh").unlink()
    store = GameProfileStore(tmp_path / "pu6e.conf")

    store.set_directory("fp", game_directory)

    profile = store.profile("fp")
    assert not profile.ready
    assert "savegame/objblkhh" in profile.missing_files


def test_game_profiles_import_legacy_configuration_and_preserve_display_settings(
    tmp_path: Path,
) -> None:
    from pu6e_qt.game_profiles import GameProfileStore

    ultima_directory = tmp_path / "ultima"
    mars_directory = tmp_path / "mars"
    write_game_fixture(ultima_directory, "fp", "ultima")
    write_game_fixture(mars_directory, "md", "mars")
    configuration_path = tmp_path / "pu6e.conf"
    configuration_path.write_text(
        "[pu6e]\n"
        f"gamedir = {ultima_directory}\n"
        "gametype = fp\n"
        "width = 1280\n"
        "height = 720\n"
        "zoom = 1.5\n"
    )
    store = GameProfileStore(configuration_path)
    assert store.profile("fp").ready
    store.set_directory("md", mars_directory)

    store.activate("md")

    saved = ConfigParser()
    saved.read(configuration_path)
    assert saved.get("pu6e", "gametype") == "md"
    assert Path(saved.get("pu6e", "gamedir")) == mars_directory.resolve()
    assert saved.getint("pu6e", "width") == 1280
    assert saved.getint("pu6e", "height") == 720
    assert saved.getfloat("pu6e", "zoom") == 1.5
    assert GameProfileStore(configuration_path).profile("fp").ready


def test_launcher_only_enables_the_stage_launch_action_for_ready_games(
    tmp_path: Path,
    launcher_app: QApplication,
) -> None:
    from pu6e_qt.game_profiles import GameProfileStore
    from pu6e_qt.launcher import LauncherWindow

    game_directory = tmp_path / "ultima"
    write_game_fixture(game_directory, "fp", "ultima")
    store = GameProfileStore(tmp_path / "pu6e.conf")
    store.set_directory("fp", game_directory)

    launcher = LauncherWindow(store)

    assert launcher.stage.launch_button.isEnabled()
    assert launcher.cards["fp"].property("launcherReady") is True
    assert launcher.cards["md"].property("launcherReady") is False
    assert launcher.cards["se"].property("launcherReady") is False
    assert all(card.settings_button.isEnabled() for card in launcher.cards.values())
    launcher.close()


def test_launcher_explains_missing_saved_world_files_with_hoverable_warning(
    tmp_path: Path,
    launcher_app: QApplication,
) -> None:
    from pu6e_qt.game_profiles import GameProfileStore
    from pu6e_qt.launcher import LauncherWindow

    game_directory = tmp_path / "mars"
    write_game_fixture(game_directory, "md", "mars")
    (game_directory / "savegame" / "objlist").unlink()
    (game_directory / "savegame" / "objblkaa").unlink()
    store = GameProfileStore(tmp_path / "pu6e.conf")
    store.set_directory("md", game_directory)

    launcher = LauncherWindow(store)

    card = launcher.cards["md"]
    assert not card.availability_button.isHidden()
    assert card.status_label.property("launcherWarning") is True
    assert "savegame/objlist" in card.availability_button.toolTip()
    assert "savegame/objblkaa" in card.availability_button.toolTip()
    assert card.status_label.toolTip() == card.availability_button.toolTip()
    assert not launcher.cards["fp"].availability_button.isHidden()
    launcher.close()


def test_game_configurator_validates_directory_before_saving(
    tmp_path: Path,
    launcher_app: QApplication,
) -> None:
    from pu6e_qt.game_profiles import GameProfileStore
    from pu6e_qt.launcher_dialog import GameConfigurationDialog

    game_directory = tmp_path / "mars"
    write_game_fixture(game_directory, "md", "mars")
    store = GameProfileStore(tmp_path / "pu6e.conf")
    dialog = GameConfigurationDialog(store, "md")
    assert not dialog.save_button.isEnabled()

    dialog.directory_field.setText(str(game_directory))
    dialog.save_button.click()

    assert store.profile("md").ready
    assert dialog.result() == dialog.DialogCode.Accepted


def test_launcher_opens_selected_game_in_editor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.game_profiles import GameProfileStore
    import pu6e_qt.launcher as launcher_module

    class StubEditor(QWidget):
        def __init__(self, controller: EditorController) -> None:
            super().__init__()
            self.controller = controller

    game_directory = tmp_path / "savage"
    write_game_fixture(game_directory, "se", "savage")
    store = GameProfileStore(tmp_path / "pu6e.conf")
    store.set_directory("se", game_directory)
    monkeypatch.setattr(launcher_module, "MainWindow", StubEditor)
    launcher = launcher_module.LauncherWindow(store)

    launcher.cards["se"].click()
    launcher.stage.launch_button.click()

    assert Config.gametype == "se"
    assert launcher.editor_window is not None
    assert launcher.editor_window.controller.position == (0x134, 0x16C, 0)
    assert launcher.editor_window.isVisible()
    launcher.editor_window.close()
    assert launcher.isVisible()
    launcher.close()
