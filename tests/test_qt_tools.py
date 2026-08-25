from __future__ import annotations

from pathlib import Path

import pytest

from test_core import write_game_fixture
from U6 import Map, book


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_goto_accepts_bounded_hexadecimal_coordinates(qapp) -> None:
    from pu6e_qt.dialogs import GoToDialog

    dialog = GoToDialog((0, 0, 0))
    dialog.x.lineEdit().setText("134")
    dialog.y.lineEdit().setText("16c")
    dialog.z.lineEdit().setText("0")

    dialog.accept()

    assert dialog.result() == dialog.DialogCode.Accepted
    assert dialog.values() == (0x134, 0x16C, 0)


def test_goto_does_not_accept_out_of_range_hexadecimal_coordinate(qapp) -> None:
    from pu6e_qt.dialogs import GoToDialog

    dialog = GoToDialog((0, 0, 0))
    dialog.x.lineEdit().setText("400")

    dialog.accept()

    assert dialog.result() != dialog.DialogCode.Accepted


def test_chunk_inspector_updates_fixture_map(tmp_path: Path, qapp) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.tools import ChunkInspector

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "tools")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    old_chunk, _, _ = Map.world_to_chunk_num(0, 0, 0)
    inspector = ChunkInspector(controller)
    inspector.set_mapchunk(0, 0, 0)

    inspector.chunk.setValue((old_chunk + 1) % 0x400)

    assert Map.world_to_chunk_num(0, 0, 0)[0] != old_chunk
    assert Map.map_dirty == 1


def test_book_viewer_is_read_only_and_handles_bookless_game_data(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    from pu6e_qt.tools import BookViewer

    monkeypatch.setattr(book, "books", [])
    viewer = BookViewer()

    assert viewer.text.isReadOnly()
    assert not viewer.book_index.isEnabled()
    assert viewer.text.toPlainText() == "No book text is available for this game."


def test_book_viewer_treats_empty_md_se_entries_as_bookless(qapp, monkeypatch: pytest.MonkeyPatch) -> None:
    from pu6e_qt.tools import BookViewer

    monkeypatch.setattr(book, "books", [""] * 128)
    viewer = BookViewer()

    assert not viewer.book_index.isEnabled()
