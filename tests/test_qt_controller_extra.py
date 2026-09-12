from __future__ import annotations

from pathlib import Path

import pytest
from game_fixtures import write_game_fixture
from PySide6.QtWidgets import QApplication

from ui.app.controller import EditorController


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def controller(tmp_path: Path, qapp: QApplication) -> EditorController:
    directory = tmp_path / "first"
    write_game_fixture(directory, "fp", "first world")
    current = EditorController()
    current.load_game(directory, "fp")
    return current


def test_save_propagates_object_writer_failure(
    controller: EditorController, monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    editor = controller.session.editor
    editor.add_object_at(editor.new_object(), 0, 0, 0)
    editor.set_chunk(0, 0, 0, 0)
    original_replace = Path.replace

    def fail_objects(path: Path, target: Path) -> Path:
        if not target.name.endswith(".bak"):
            calls.append({"objblkaa": "objects", "objlist": "npcs", "map": "map"}[target.name])
            raise OSError("disk full")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_objects)

    with pytest.raises(OSError, match="disk full"):
        controller.save()

    assert calls == ["objects"]


def test_controllers_keep_independent_worlds_and_undo_history(
    controller: EditorController, tmp_path: Path,
) -> None:
    first_session = controller.session
    controller.set_position(12, 34, 0)
    controller.paint_tile(1, 0, 0, 0)
    first_session.state.npcs[0].quality = 9
    directory = tmp_path / "second"
    write_game_fixture(directory, "fp", "second world")
    second = EditorController()
    second.load_game(directory, "fp")
    second.paint_tile(2, 0, 0, 0)

    controller.undo_stack.undo()

    assert controller.session is first_session
    assert controller.position == (12, 34, 0)
    assert first_session.state.assets.catalog.name_for_tile(0) == "first world"
    assert second.session.state.assets.catalog.name_for_tile(0) == "second world"
    assert first_session.editor.map_tile_at(0, 0, 0) == 0
    assert second.session.editor.map_tile_at(0, 0, 0) == 2
    assert first_session.state.npcs[0].quality == 9
    assert second.session.state.npcs[0].quality == 0
    assert not controller.dirty
    assert second.dirty
    assert second.undo_stack.canUndo()


def test_failed_load_preserves_session_selection_and_pending_undo(
    controller: EditorController, tmp_path: Path,
) -> None:
    session = controller.session
    item = session.editor.new_object()
    controller.select_object(item)
    controller.select_location(12, 34, 0)
    controller.set_position(12, 34, 0)
    controller.paint_tile(1, 0, 0, 0)

    with pytest.raises(FileNotFoundError):
        controller.load_game(tmp_path / "missing", "fp")

    assert controller.session is session
    assert controller.selected_object is item
    assert controller.selected_location == (12, 34, 0)
    assert controller.position == (12, 34, 0)
    assert session.editor.map_tile_at(0, 0, 0) == 1
    assert controller.undo_stack.canUndo()
    assert controller.dirty


def test_commands_keep_originating_session_after_controller_replacement(
    controller: EditorController, tmp_path: Path,
) -> None:
    from ui.app.commands import ChunkSetCommand, TilePaintCommand

    session = controller.session
    tile_command = TilePaintCommand(session.editor, 7, 0, 0, 0)
    chunk_command = ChunkSetCommand(session.editor, 1, 8, 0, 0)
    directory = tmp_path / "replacement"
    write_game_fixture(directory, "fp", "replacement")
    controller.load_game(directory, "fp")

    tile_command.redo()
    chunk_command.redo()

    assert session.editor.map_tile_at(0, 0, 0) == 7
    assert session.editor.chunk_at(8, 0, 0)[0] == 1
    assert controller.session.editor.map_tile_at(0, 0, 0) == 0
    assert controller.session.editor.chunk_at(8, 0, 0)[0] == 0
    assert not controller.dirty


def test_replacing_session_clears_undo_without_changing_previous_world(
    controller: EditorController, tmp_path: Path,
) -> None:
    session = controller.session
    controller.paint_tile(4, 0, 0, 0)
    directory = tmp_path / "replacement"
    write_game_fixture(directory, "fp", "replacement")

    controller.load_game(directory, "fp")

    assert not controller.undo_stack.canUndo()
    assert not controller.undo_stack.canRedo()
    assert session.editor.map_tile_at(0, 0, 0) == 4
    assert controller.session.editor.map_tile_at(0, 0, 0) == 0
    assert not controller.dirty
