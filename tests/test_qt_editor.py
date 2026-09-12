from __future__ import annotations

from pathlib import Path

import pytest
from game_fixtures import write_game_fixture
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("game", "label"),
    (("fp", "false prophet"), ("md", "martian dreams"), ("se", "savage empire")),
)
def test_qt_controller_loads_every_supported_game(tmp_path: Path, game: str, label: str) -> None:
    from pu6e_qt.controller import EditorController

    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, label)

    controller = EditorController()
    controller.load_game(game_dir, game)

    assert controller.session.state.game_dir == game_dir.resolve()
    assert controller.session.state.game_type == game
    assert controller.session.state.assets.catalog.name_for_tile(0) == label
    assert len(controller.session.state.assets.tiles.pixels) == 2048
    assert len(controller.session.state.terrain.superchunks) == 69
    assert len(controller.session.state.object_blocks) == 69
    assert len(controller.session.state.npcs) == 256


def test_qt_controller_preserves_save_write_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pu6e_qt.controller import EditorController

    calls: list[str] = []
    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "save order")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    editor = controller.session.editor
    editor.add_object_at(editor.new_object(), 0, 0, 0)
    editor.set_chunk(0, 0, 0, 0)
    original_replace = Path.replace

    def record_write(path: Path, target: Path) -> Path:
        if not target.name.endswith(".bak"):
            calls.append({"objblkaa": "objects", "objlist": "npcs", "map": "map"}[target.name])
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", record_write)

    controller.save()

    assert calls == ["objects", "npcs", "map"]


def test_qt_controller_rejects_invalid_background_tile() -> None:
    from pu6e_qt.controller import EditorController, InvalidBackgroundTileError

    with pytest.raises(InvalidBackgroundTileError):
        EditorController().paint_tile(256, 0, 0, 0)


def test_qt_terrain_edits_support_undo_and_redo(tmp_path: Path, qapp: QApplication) -> None:
    from pu6e_qt.controller import EditorController

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "terrain")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    original_tile = controller.session.editor.map_tile_at(0, 0, 0)

    controller.paint_tile(1, 0, 0, 0)
    assert controller.session.editor.map_tile_at(0, 0, 0) == 1
    assert controller.undo_stack.canUndo()
    assert controller.dirty

    controller.undo_stack.undo()
    assert controller.session.editor.map_tile_at(0, 0, 0) == original_tile
    assert not controller.dirty

    controller.undo_stack.redo()
    assert controller.session.editor.map_tile_at(0, 0, 0) == 1
    assert controller.dirty


def test_object_inspector_updates_selected_object(tmp_path: Path, qapp: QApplication) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.inspectors import ObjectInspector

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "object")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    current = controller.session.editor.new_object()
    controller.session.editor.add_object_at(current, 0, 0, 0)
    inspector = ObjectInspector(controller)

    inspector.set_object(current)
    inspector.quality.setValue(42)

    assert current.quality == 42
    assert controller.session.state.dirty_object_blocks


def test_object_stack_populates_selected_point(tmp_path: Path, qapp: QApplication) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.inspectors import ObjectStack

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "stack")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    current = controller.session.editor.new_object()
    controller.session.editor.add_object_at(current, 0, 0, 0)
    point = controller.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(controller)

    stack.set_point(point, 0, 0, 0)

    assert stack.tree.topLevelItemCount() == 1
    assert stack.tree.currentItem() is not None


def test_hex_coordinate_box_parses_hexadecimal(qapp: QApplication) -> None:
    from pu6e_qt.widgets import HexSpinBox

    coordinate = HexSpinBox(0x3FF)
    coordinate.setValue(0x16C)

    assert coordinate.text() == "16c"
    assert coordinate.valueFromText("134") == 0x134


def test_active_entrypoint_does_not_import_wx() -> None:
    import ast

    entrypoint = Path(__file__).resolve().parents[1] / "pu6e.py"
    imported_names = {
        node.module or ""
        for node in ast.walk(ast.parse(entrypoint.read_text()))
        if isinstance(node, ast.ImportFrom)
    }
    imported_names.update(
        alias.name
        for node in ast.walk(ast.parse(entrypoint.read_text()))
        if isinstance(node, ast.Import)
        for alias in node.names
    )

    assert "mapedit_wxgl" not in imported_names
    assert "wx" not in imported_names
