from __future__ import annotations

import shutil
import struct
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from test_core import write_game_fixture
from pu6e_qt.application import RuntimeConfiguration
from pu6e_qt.controller import EditorController
from pu6e_qt.game_profiles import GameProfile
from pu6e_qt.launcher import LauncherWindow


@pytest.fixture(scope="session")
def launcher_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def critical_dialogs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[QWidget | None, str, str]]:
    dialogs: list[tuple[QWidget | None, str, str]] = []

    def record(parent: QWidget | None, title: str, text: str) -> None:
        dialogs.append((parent, title, text))

    monkeypatch.setattr(QMessageBox, "critical", record)
    return dialogs


def _configured_launcher(tmp_path: Path, game: str) -> tuple[LauncherWindow, Path]:
    from pu6e_qt.game_profiles import GameProfileStore

    game_directory = tmp_path / game
    write_game_fixture(game_directory, game, game)
    store = GameProfileStore(tmp_path / "pu6e.conf")
    store.set_directory(game, game_directory)
    launcher = LauncherWindow(store)
    launcher.show()
    return launcher, game_directory


def _track_card_refresh(
    launcher: LauncherWindow, game: str, monkeypatch: pytest.MonkeyPatch
) -> list[GameProfile]:
    refreshed_profiles: list[GameProfile] = []
    update_profile = launcher.cards[game].update_profile

    def record(profile: GameProfile) -> None:
        refreshed_profiles.append(profile)
        update_profile(profile)

    monkeypatch.setattr(launcher.cards[game], "update_profile", record)
    return refreshed_profiles


def _assert_failed_launch(
    launcher,
    dialogs: list[tuple[QWidget | None, str, str]],
    game: str,
    game_title: str,
    expected: str,
    card_ready: bool,
) -> None:
    assert len(dialogs) == 1
    parent, title, text = dialogs[0]
    assert parent is launcher
    assert game_title in title
    assert expected in text
    assert launcher.isVisible()
    assert launcher.editor_window is None
    assert launcher.cards[game].property("launcherReady") is card_ready


def test_launcher_refreshes_game_when_ready_installation_disappears(
    tmp_path: Path,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a launcher card built from a complete Ultima VI fixture.
    launcher, game_directory = _configured_launcher(tmp_path, "fp")
    shutil.rmtree(game_directory)

    # When: the installation is removed after the card reports ready.
    launcher.launch_game("fp")

    # Then: the launcher reports the current diagnosis without opening an editor.
    _assert_failed_launch(
        launcher, critical_dialogs, "fp", "Ultima VI", "Game directory does not exist", False
    )
    launcher.close()


def test_launcher_refreshes_game_when_required_file_disappears(
    tmp_path: Path,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a launcher card built from a complete Martian Dreams fixture.
    launcher, game_directory = _configured_launcher(tmp_path, "md")
    (game_directory / "mdpal").unlink()

    # When: its palette is removed after the card reports ready.
    launcher.launch_game("md")

    # Then: the card and native error describe the missing palette.
    _assert_failed_launch(
        launcher, critical_dialogs, "md", "Martian Dreams", "Game palette is missing", False
    )
    launcher.close()


def test_launcher_reports_configuration_error_without_hiding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a configured Savage Empire launcher and a malformed runtime config.
    from pu6e_qt.application import MalformedConfigurationError
    import pu6e_qt.application as application_module
    import pu6e_qt.launcher as launcher_module

    launcher, _ = _configured_launcher(tmp_path, "se")
    error = MalformedConfigurationError(launcher.store.config_path, "invalid width")
    refreshed_profiles = _track_card_refresh(launcher, "se", monkeypatch)

    def reject_configuration(_config_path: Path) -> RuntimeConfiguration:
        raise error

    monkeypatch.setattr(application_module, "read_configuration", reject_configuration)

    # When: initialization rejects the generated configuration.
    launcher.launch_game("se")

    # Then: the launcher stays available and explains which config to repair.
    _assert_failed_launch(
        launcher,
        critical_dialogs,
        "se",
        "The Savage Empire",
        str(launcher.store.config_path),
        True,
    )
    assert refreshed_profiles == [launcher.store.profile("se")]
    launcher.close()


def test_launcher_reports_expected_loader_file_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a complete Ultima VI fixture whose loader cannot read a resource.
    launcher, game_directory = _configured_launcher(tmp_path, "fp")
    missing_resource = game_directory / "map"
    error = FileNotFoundError(missing_resource)
    refreshed_profiles = _track_card_refresh(launcher, "fp", monkeypatch)

    def fail_loader(_controller: EditorController, _directory: Path, _game: str) -> None:
        raise error

    monkeypatch.setattr(EditorController, "load_game", fail_loader)

    # When: the editor loader reports its expected filesystem failure.
    launcher.launch_game("fp")

    # Then: one actionable native dialog retains the visible launcher.
    _assert_failed_launch(
        launcher, critical_dialogs, "fp", "Ultima VI", str(missing_resource), True
    )
    assert refreshed_profiles == [launcher.store.profile("fp")]
    launcher.close()


def test_launcher_reports_expected_loader_parse_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a complete Martian Dreams fixture with a malformed resource library.
    launcher, game_directory = _configured_launcher(tmp_path, "md")
    refreshed_profiles = _track_card_refresh(launcher, "md", monkeypatch)
    (game_directory / "look.lzc").write_bytes(struct.pack("<IH", 100, 6) + b"bad")

    # When: the loader reports its expected parse failure.
    launcher.launch_game("md")

    # Then: the launcher presents the parse cause without constructing an editor.
    _assert_failed_launch(
        launcher, critical_dialogs, "md", "Martian Dreams", "File size", True
    )
    assert refreshed_profiles == [launcher.store.profile("md")]
    launcher.close()


def test_launcher_reports_truncated_palette_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: a complete Savage Empire fixture with a truncated palette parser result.
    launcher, game_directory = _configured_launcher(tmp_path, "se")
    refreshed_profiles = _track_card_refresh(launcher, "se", monkeypatch)
    (game_directory / "sepal").write_bytes(b"\x01")

    # When: the palette parser reports truncation.
    launcher.launch_game("se")

    # Then: the launcher keeps the selected game available for correction and retry.
    _assert_failed_launch(
        launcher,
        critical_dialogs,
        "se",
        "The Savage Empire",
        "unpack requires a buffer of 3 bytes",
        True,
    )
    assert refreshed_profiles == [launcher.store.profile("se")]
    launcher.close()


def test_launcher_can_retry_after_restoring_game_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    launcher_app: QApplication,
    critical_dialogs: list[tuple[QWidget | None, str, str]],
) -> None:
    # Given: an initially complete Ultima VI fixture with a removed palette.
    import pu6e_qt.launcher as launcher_module

    class StubEditor(QWidget):
        def __init__(self, controller: EditorController) -> None:
            super().__init__()
            self.controller = controller

    launcher, game_directory = _configured_launcher(tmp_path, "fp")
    palette = game_directory / "u6pal"
    palette.unlink()
    monkeypatch.setattr(launcher_module, "MainWindow", StubEditor)

    # When: the fixture is repaired and launch is retried after a failed launch.
    launcher.launch_game("fp")
    palette.write_bytes(bytes((1,)) * 768)
    launcher.launch_game("fp")

    # Then: the restored installation opens an editor after exactly one prior dialog.
    assert len(critical_dialogs) == 1
    assert launcher.editor_window is not None
    assert launcher.editor_window.isVisible()
    launcher.editor_window.close()
    launcher.close()
