from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QWidget

from pu6e_qt.game_profiles import GameProfileStore
from pu6e_qt.launcher import LauncherWindow
from pu6e_qt.renderer_settings import RendererMode, RendererRuntime
from test_core import write_game_fixture


@pytest.fixture(scope="session")
def atlas_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def atlas_launcher(tmp_path: Path, atlas_app: QApplication) -> LauncherWindow:
    store = GameProfileStore(tmp_path / "launcher.conf")
    for game in ("fp", "md", "se"):
        directory = tmp_path / game
        write_game_fixture(directory, game, game)
        store.set_directory(game, directory)
    (tmp_path / "md" / "savegame" / "objlist").unlink()
    launcher = LauncherWindow(store, RendererRuntime(RendererMode.OPENGL))
    launcher.show()
    atlas_app.processEvents()
    yield launcher
    launcher.close()


def test_atlas_uses_a_horizontal_world_rail_and_cinematic_stage(
    atlas_launcher: LauncherWindow,
) -> None:
    rail = atlas_launcher.findChild(QWidget, "atlas-world-rail")
    stage = atlas_launcher.findChild(QWidget, "atlas-world-stage")

    assert rail is not None
    assert stage is not None
    assert rail.width() < stage.width()
    assert tuple(atlas_launcher.cards) == ("fp", "md", "se")
    assert all(
        card.height() >= card.layout().minimumSize().height()
        for card in atlas_launcher.cards.values()
    )


def test_selecting_another_world_updates_the_selected_stage(
    atlas_launcher: LauncherWindow,
) -> None:
    atlas_launcher.cards["se"].click()

    assert atlas_launcher.selected_game == "se"
    assert atlas_launcher.stage.title_label.text() == "The Savage Empire"
    assert atlas_launcher.cards["se"].isChecked()
    assert not atlas_launcher.cards["fp"].isChecked()


def test_unavailable_world_keeps_its_diagnosis_and_recovery_visible(
    atlas_launcher: LauncherWindow,
) -> None:
    atlas_launcher.cards["md"].click()

    assert not atlas_launcher.stage.launch_button.isEnabled()
    assert "saved game" in atlas_launcher.stage.status_label.text().lower()
    assert "savegame/objlist" in atlas_launcher.stage.availability_button.toolTip()
    assert atlas_launcher.stage.configure_button.isEnabled()


def test_ready_world_has_one_primary_stage_launch_action(
    atlas_launcher: LauncherWindow,
) -> None:
    atlas_launcher.cards["fp"].click()

    assert atlas_launcher.stage.launch_button.isEnabled()
    assert atlas_launcher.stage.launch_button.accessibleName() == "Launch Ultima VI editor"
    assert atlas_launcher.stage.availability_button.isHidden()


def test_unconfigured_diagnostic_is_not_elided_at_minimum_size(
    tmp_path: Path, atlas_app: QApplication
) -> None:
    launcher = LauncherWindow(
        GameProfileStore(tmp_path / "launcher.conf"),
        RendererRuntime(RendererMode.OPENGL),
    )
    launcher.resize(860, 560)
    launcher.show()
    atlas_app.processEvents()

    path_label = launcher.stage.path_label
    assert path_label.text() == "No folder selected"
    assert path_label.fontMetrics().horizontalAdvance(path_label.text()) <= path_label.width()
    launcher.close()


@pytest.mark.parametrize("game", ["fp", "md", "se"])
def test_world_artwork_renders_into_a_native_qt_pixmap(
    atlas_launcher: LauncherWindow,
    game: str,
) -> None:
    atlas_launcher.cards[game].click()

    assert not atlas_launcher.stage.grab().isNull()
