from __future__ import annotations

from pathlib import Path

import pytest

from test_core import write_game_fixture
from U6 import Config, Map, NPCs, look, obj, tile


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

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

    assert Config.gamedir == str(game_dir.resolve())
    assert Config.gametype == game
    assert look.get_obj_name(0) == label
    assert len(tile.maptiles) == 2048
    assert len(Map.map) == 69
    assert len(obj.objblk) == 69
    assert len(NPCs.npcs) == 256


def test_qt_controller_preserves_save_write_order(monkeypatch: pytest.MonkeyPatch) -> None:
    from pu6e_qt.controller import EditorController

    calls: list[str] = []
    monkeypatch.setattr(obj, "write_changes", lambda: calls.append("objects"))
    monkeypatch.setattr(NPCs, "write", lambda: calls.append("npcs"))
    monkeypatch.setattr(Map, "write_changes", lambda: calls.append("map"))

    EditorController().save()

    assert calls == ["objects", "npcs", "map"]


def test_qt_controller_rejects_invalid_background_tile() -> None:
    from pu6e_qt.controller import EditorController, InvalidBackgroundTileError

    with pytest.raises(InvalidBackgroundTileError):
        EditorController().paint_tile(256, 0, 0, 0)


def test_qt_terrain_edits_support_undo_and_redo(tmp_path: Path, qapp) -> None:
    from pu6e_qt.controller import EditorController

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "terrain")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    original_tile = Map.maptile_at(0, 0, 0)

    controller.paint_tile(1, 0, 0, 0)
    assert Map.maptile_at(0, 0, 0) == 1
    assert controller.undo_stack.canUndo()
    assert controller.dirty

    controller.undo_stack.undo()
    assert Map.maptile_at(0, 0, 0) == original_tile
    assert not controller.dirty

    controller.undo_stack.redo()
    assert Map.maptile_at(0, 0, 0) == 1
    assert controller.dirty


def test_object_inspector_updates_selected_object(tmp_path: Path, qapp) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.inspectors import ObjectInspector

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "object")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    current = obj.default_object()
    obj.add_object_at(current, 0, 0, 0)
    inspector = ObjectInspector(controller)

    inspector.set_object(current)
    inspector.quality.setValue(42)

    assert current.quality == 42
    assert obj.changes


def test_object_stack_populates_selected_point(tmp_path: Path, qapp) -> None:
    from pu6e_qt.controller import EditorController
    from pu6e_qt.inspectors import ObjectStack

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "stack")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    current = obj.default_object()
    obj.add_object_at(current, 0, 0, 0)
    point = obj.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(controller)

    stack.set_point(point, 0, 0, 0)

    assert stack.tree.topLevelItemCount() == 1
    assert stack.tree.currentItem() is not None


def test_hex_coordinate_box_parses_hexadecimal(qapp) -> None:
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
