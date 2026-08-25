from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from pu6e_qt import game_profiles
from pu6e_qt.game_profiles import GameProfileStore
from test_core import write_game_fixture
from U6 import pal

GAMES = ("fp", "md", "se")


@pytest.fixture(scope="session")
def launcher_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _dialog(tmp_path: Path, game: str):
    from pu6e_qt.launcher_dialog import GameConfigurationDialog

    store = GameProfileStore(tmp_path / "pu6e.conf")
    return store, GameConfigurationDialog(store, game)


def _installation(tmp_path: Path, game: str, directory_name: str | None = None) -> Path:
    directory = tmp_path / (directory_name or game)
    write_game_fixture(directory, game, game)
    return directory


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_explains_empty_directory(
    tmp_path: Path, launcher_app: QApplication, game: str
) -> None:
    # Given: a game with no configured installation.
    _store, dialog = _dialog(tmp_path, game)

    # When: its directory field remains blank.
    dialog.directory_field.setText("   ")

    # Then: saving is disabled with specific recovery guidance.
    assert not dialog.save_button.isEnabled()
    assert "directory" in dialog.status_label.text().lower()
    assert "select" in dialog.status_label.text().lower()


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_expands_to_show_multiline_error_without_clipping(
    tmp_path: Path, launcher_app: QApplication, game: str
) -> None:
    _store, dialog = _dialog(tmp_path, game)
    dialog.show()
    launcher_app.processEvents()

    dialog.directory_field.setText(str(tmp_path / "missing-game-installation"))
    launcher_app.processEvents()

    required_height = dialog.status_label.heightForWidth(dialog.status_label.width())
    assert dialog.status_label.height() >= required_height
    dialog.close()


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_distinguishes_missing_and_non_directory_paths(
    tmp_path: Path, launcher_app: QApplication, game: str
) -> None:
    # Given: a missing path and a regular file.
    _store, dialog = _dialog(tmp_path, game)
    missing = tmp_path / "not-installed"
    regular_file = tmp_path / "not-a-directory"
    regular_file.write_text("not a game")

    # When: each path is selected.
    dialog.directory_field.setText(str(missing))

    # Then: the missing path is named and saving remains disabled.
    assert not dialog.save_button.isEnabled()
    assert "does not exist" in dialog.status_label.text().lower()
    assert str(missing.resolve()) in dialog.status_label.text()

    # When: a file is selected instead.
    dialog.directory_field.setText(str(regular_file))

    # Then: the distinct non-directory category and actual file are shown.
    assert not dialog.save_button.isEnabled()
    assert "not a directory" in dialog.status_label.text().lower()
    assert str(regular_file.resolve()) in dialog.status_label.text()


@pytest.mark.parametrize(
    ("expected_game", "actual_game"),
    tuple((expected, actual) for expected in GAMES for actual in GAMES if expected != actual),
)
def test_configuration_dialog_identifies_wrong_supported_game(
    tmp_path: Path, launcher_app: QApplication, expected_game: str, actual_game: str
) -> None:
    # Given: a complete installation for another supported game.
    directory = _installation(tmp_path, actual_game)
    _store, dialog = _dialog(tmp_path, expected_game)

    # When: it is selected for this game.
    dialog.directory_field.setText(str(directory))

    # Then: both expected and detected titles explain why saving is disabled.
    assert not dialog.save_button.isEnabled()
    status = dialog.status_label.text()
    assert "different game installation" in status.lower()
    assert dialog.windowTitle().removeprefix("Configure ") in status
    assert {"fp": "Ultima VI", "md": "Martian Dreams", "se": "The Savage Empire"}[actual_game] in status
    assert "select the complete installation" in status.lower()


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("resource", ("palette", "tileflag"))
def test_configuration_dialog_explains_missing_palette_or_core_data(
    tmp_path: Path, launcher_app: QApplication, game: str, resource: str
) -> None:
    # Given: a complete game installation missing one required asset.
    directory = _installation(tmp_path, game)
    missing = pal.paths[game] if resource == "palette" else "tileflag"
    (directory / missing).unlink()
    _store, dialog = _dialog(tmp_path, game)

    # When: the incomplete installation is selected.
    dialog.directory_field.setText(str(directory))

    # Then: its category, filename, and copy-complete-installation remedy are visible.
    assert not dialog.save_button.isEnabled()
    status = dialog.status_label.text()
    assert ("palette is missing" if resource == "palette" else "required game files are missing") in status.lower()
    assert missing in status
    assert "copy a complete installation" in status.lower()


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("missing_directory", (False, True))
def test_configuration_dialog_explains_missing_saved_world(
    tmp_path: Path, launcher_app: QApplication, game: str, missing_directory: bool
) -> None:
    # Given: a game installation whose saved-world data is absent.
    directory = _installation(tmp_path, game)
    if missing_directory:
        shutil.rmtree(directory / "savegame")
    else:
        (directory / "savegame" / "objlist").unlink()
        for block in (directory / "savegame").glob("objblk*"):
            block.unlink()
    _store, dialog = _dialog(tmp_path, game)

    # When: it is selected.
    dialog.directory_field.setText(str(directory))

    # Then: the grouped saved-world diagnostic and recovery action are visible.
    assert not dialog.save_button.isEnabled()
    status = dialog.status_label.text()
    assert (
        "saved game directory is missing"
        if missing_directory
        else "saved game files are missing"
    ) in status.lower()
    assert "savegame" in status
    if not missing_directory:
        assert "69 saved-world object blocks" in status
    assert "start the original game and create a save first" in status.lower()


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_explains_case_and_permission_failures(
    tmp_path: Path, launcher_app: QApplication, game: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a case-mismatched installation and a complete readable installation.
    case_directory = _installation(tmp_path, game, f"{game}-case")
    expected_name = pal.paths[game]
    actual_name = expected_name.upper()
    (case_directory / expected_name).rename(case_directory / actual_name)
    readable_directory = _installation(tmp_path, game, f"{game}-readable")
    _store, dialog = _dialog(tmp_path, game)

    # When: the capitalization mismatch is selected.
    dialog.directory_field.setText(str(case_directory))

    # Then: the expected and actual names plus rename recovery are visible.
    assert not dialog.save_button.isEnabled()
    status = dialog.status_label.text()
    assert "incorrect capitalization" in status.lower()
    assert expected_name in status
    assert actual_name in status
    assert "rename the game files" in status.lower()

    # When: the selected directory is denied read access at the narrow inspection seam.
    monkeypatch.setattr(game_profiles, "_is_readable", lambda path: path != readable_directory)
    dialog.directory_field.setText(str(readable_directory))

    # Then: the read-specific failure and recovery are visible.
    assert not dialog.save_button.isEnabled()
    status = dialog.status_label.text()
    assert "cannot be read" in status.lower()
    assert str(readable_directory) in status
    assert "allow read access" in status.lower()


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_stays_open_when_config_write_fails(
    tmp_path: Path, launcher_app: QApplication, game: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a valid game installation and a configuration store that cannot persist.
    directory = _installation(tmp_path, game)
    store, dialog = _dialog(tmp_path, game)
    dialog.directory_field.setText(str(directory))
    dialog.show()

    def fail_to_write(_game: str, _directory: Path) -> None:
        raise PermissionError("configuration file is read-only")

    monkeypatch.setattr(store, "set_directory", fail_to_write)

    # When: Save is clicked.
    dialog.save_button.click()

    # Then: the dialog and entered value survive with actionable persistence detail.
    assert dialog.isVisible()
    assert dialog.directory_field.text() == str(directory)
    assert dialog.result() != dialog.DialogCode.Accepted
    status = dialog.status_label.text()
    assert str(store.config_path) in status
    assert "read-only" in status.lower()
    assert "write" in status.lower()
    dialog.close()


@pytest.mark.parametrize("game", GAMES)
def test_configuration_dialog_accepts_valid_installation(
    tmp_path: Path, launcher_app: QApplication, game: str
) -> None:
    # Given: a complete game installation.
    directory = _installation(tmp_path, game)
    store, dialog = _dialog(tmp_path, game)

    # When: it is selected and saved.
    dialog.directory_field.setText(str(directory))
    dialog.save_button.click()

    # Then: persistence succeeds and the normal accepted result remains intact.
    assert dialog.save_button.isEnabled()
    assert store.profile(game).ready
    assert dialog.result() == dialog.DialogCode.Accepted
