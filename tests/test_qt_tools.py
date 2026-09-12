from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from game_fixtures import write_game_fixture
from PySide6.QtWidgets import QApplication

from ui.app.controller import EditorController


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tools_controller(tmp_path: Path, qapp: QApplication) -> EditorController:
    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "tools")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    return controller


def test_goto_accepts_bounded_hexadecimal_coordinates(qapp: QApplication) -> None:
    from ui.app.map.dialogs import GoToDialog

    dialog = GoToDialog((0, 0, 0))
    dialog.x.lineEdit().setText("134")
    dialog.y.lineEdit().setText("16c")
    dialog.z.lineEdit().setText("0")

    dialog.accept()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.values() == (0x134, 0x16C, 0)


def test_goto_does_not_accept_out_of_range_hexadecimal_coordinate(qapp: QApplication) -> None:
    from ui.app.map.dialogs import GoToDialog

    dialog = GoToDialog((0, 0, 0))
    dialog.x.lineEdit().setText("400")

    dialog.accept()

    assert dialog.result() != dialog.DialogCode.Accepted


def test_chunk_inspector_updates_fixture_map(tools_controller: EditorController) -> None:
    from ui.app.terrain.chunks import ChunkInspector

    controller = tools_controller
    old_chunk, _, _ = controller.session.editor.chunk_at(0, 0, 0)
    inspector = ChunkInspector(controller)
    inspector.set_mapchunk(0, 0, 0)

    inspector.chunk.setValue((old_chunk + 1) % 0x400)

    assert controller.session.editor.chunk_at(0, 0, 0)[0] != old_chunk
    assert controller.session.state.terrain.map_dirty


def test_book_viewer_is_read_only_and_handles_bookless_game_data(tools_controller: EditorController) -> None:
    from ui.app.books.viewer import BookViewer

    state = tools_controller.session.state
    state.assets = replace(state.assets, books=())
    viewer = BookViewer(tools_controller)

    assert viewer.text.isReadOnly()
    assert not viewer.book_index.isEnabled()
    assert viewer.text.toPlainText() == "No book text is available for this game."


def test_book_viewer_treats_empty_md_se_entries_as_bookless(tools_controller: EditorController) -> None:
    from ui.app.books.viewer import BookViewer

    state = tools_controller.session.state
    state.assets = replace(state.assets, books=("",) * 128)
    viewer = BookViewer(tools_controller)

    assert not viewer.book_index.isEnabled()


def test_book_viewer_replaces_text_when_controller_loads_another_game(
    tools_controller: EditorController, tmp_path: Path,
) -> None:
    from ui.app.books.viewer import BookViewer

    state = tools_controller.session.state
    state.assets = replace(state.assets, books=("First world book",))
    viewer = BookViewer(tools_controller)
    assert viewer.text.toPlainText() == "First world book"
    directory = tmp_path / "second"
    write_game_fixture(directory, "fp", "second")
    (directory / "book.dat").write_bytes(bytes(256) + b"Second world book\0")

    tools_controller.load_game(directory, "fp")

    assert viewer.text.toPlainText() == "Second world book"
    assert viewer.book_index.isEnabled()


def test_tile_browser_replaces_catalog_when_controller_loads_another_game(
    tools_controller: EditorController, tmp_path: Path,
) -> None:
    from ui.app.terrain.tiles import TileBrowser

    browser = TileBrowser(tools_controller)
    assert "tools" in browser.grid.item(0).text()
    directory = tmp_path / "second"
    write_game_fixture(directory, "fp", "second tiles")

    tools_controller.load_game(directory, "fp")

    assert "second tiles" in browser.grid.item(0).text()
    assert browser.selected_tile() == tools_controller.selected_tile
