from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from game_fixtures import write_game_fixture
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.app.controller import EditorController


@pytest.fixture(scope="session")
def application() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def game(tmp_path: Path, application: QApplication) -> EditorController:
    from ui.app.controller import EditorController

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "inspected object")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    return controller


def test_inspector_population_does_not_dirty_the_world(game: EditorController) -> None:
    from ui.app.objects.inspector import ObjectInspector

    current = game.session.editor.new_object()
    current.quality = 17
    game.session.editor.clear_changes()

    inspector = ObjectInspector(game)
    inspector.set_object(current)

    assert inspector.quality.value() == 17
    assert not game.session.state.dirty_object_blocks


def test_inspector_fields_mutate_original_and_bound_status(game: EditorController) -> None:
    from ui.app.objects.inspector import ObjectInspector

    current = game.session.editor.new_object()
    inspector = ObjectInspector(game)
    inspector.set_object(current)

    inspector.quantity.setValue(5)
    inspector.quality.setValue(42)
    inspector.status.setValue(0xAB)

    assert (current.quantity, current.quality, current.status) == (5, 42, 0xAB)
    assert inspector.status.maximum() == 0xFF
    assert inspector.weight.isReadOnly()


def test_inspector_empty_selection_disables_fields(game: EditorController) -> None:
    from ui.app.objects.inspector import ObjectInspector

    inspector = ObjectInspector(game)

    inspector.set_object(None)

    assert not inspector.quality.isEnabled()


def test_stack_displays_nested_real_objects_and_selects_topmost(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    parent = game.session.editor.new_object()
    child = game.session.editor.new_object()
    parent.insert(0, child)
    game.session.editor.add_object_at(parent, 0, 0, 0)
    point = game.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(game)

    stack.set_point(point, 0, 0, 0)

    assert stack.tree.topLevelItemCount() == 1
    assert stack.tree.topLevelItem(0).childCount() == 1
    assert game.selected_object is parent


def test_stack_copy_paste_after_clones_once_and_consumes_clipboard(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    original = game.session.editor.new_object()
    game.session.editor.add_object_at(original, 0, 0, 0)
    point = game.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(game)
    stack.set_point(point, 0, 0, 0)

    stack.copy_selected()
    stack.paste_after()

    assert len(point) == 2
    assert point[0] is original
    assert point[1] is not original
    assert stack.clipboard is None


def test_stack_cut_and_paste_into_preserves_identity(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    container = game.session.editor.new_object()
    moving = game.session.editor.new_object()
    game.session.editor.add_object_at(container, 0, 0, 0)
    game.session.editor.add_object_at(moving, 0, 0, 0)
    point = game.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(game)
    stack.set_point(point, 0, 0, 0)

    stack.cut_selected()
    stack.tree.setCurrentItem(stack.tree.topLevelItem(0))
    stack.paste_into()

    assert list(point) == [container]
    assert container.contains == [moving]
    assert stack.clipboard is None


def test_stack_move_rejects_descendant_cycle(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    parent = game.session.editor.new_object()
    child = game.session.editor.new_object()
    parent.insert(0, child)
    game.session.editor.add_object_at(parent, 0, 0, 0)
    point = game.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(game)
    stack.set_point(point, 0, 0, 0)
    game.session.editor.clear_changes()

    moved = stack.move_object(parent, child)

    assert moved is False
    assert list(point) == [parent]
    assert parent.contains == [child]
    assert not game.session.state.dirty_object_blocks


def test_stack_empty_location_does_not_create_or_dirty_point(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    stack = ObjectStack(game)
    game.session.editor.clear_changes()

    stack.set_point(None, 0x134, 0x16C, 0)

    assert stack.tree.topLevelItemCount() == 0
    assert stack.position.text() == "Position: 134, 16c, 0"
    assert not game.session.state.dirty_object_blocks


def test_stack_can_create_and_paste_into_an_empty_location(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    stack = ObjectStack(game)
    stack.set_point(None, 0x134, 0x16C, 0)

    stack.create_default()
    stack.paste_after()

    point = game.session.editor.objects_at(0x134, 0x16C, 0)
    assert point is not None
    assert len(point) == 1
    assert stack.tree.topLevelItemCount() == 1
    assert stack.clipboard is None
    assert game.dirty


def test_stack_native_keyboard_copy_paste_drives_game_objects(game: EditorController) -> None:
    from ui.app.objects.tree import ObjectStack

    original = game.session.editor.new_object()
    game.session.editor.add_object_at(original, 0, 0, 0)
    point = game.session.editor.objects_at(0, 0, 0)
    assert point is not None
    stack = ObjectStack(game)
    stack.set_point(point, 0, 0, 0)
    stack.show()
    stack.tree.setFocus()
    QApplication.processEvents()

    QTest.keyClick(stack.tree, Qt.Key.Key_C)
    QTest.keyClick(stack.tree, Qt.Key.Key_V)

    assert len(point) == 2
    assert point[0] is original
    assert point[1] is not original
    assert stack.clipboard is None


def test_inspector_and_stack_clear_old_objects_when_session_changes(
    game: EditorController, tmp_path: Path,
) -> None:
    from ui.app.objects.inspector import ObjectInspector
    from ui.app.objects.tree import ObjectStack

    previous_session = game.session
    original = previous_session.editor.new_object()
    previous_session.editor.add_object_at(original, 0, 0, 0)
    stack = ObjectStack(game)
    stack.set_point(previous_session.editor.objects_at(0, 0, 0), 0, 0, 0)
    stack.set_default_obj(original)
    stack.copy_selected()
    inspector = ObjectInspector(game)
    inspector.set_object(original)
    directory = tmp_path / "replacement"
    write_game_fixture(directory, "fp", "replacement object")

    game.load_game(directory, "fp")

    assert inspector.current_object is None
    assert not inspector.quality.isEnabled()
    assert stack.point is None
    assert stack.clipboard is None
    assert stack.default_object is None
    assert stack.tree.topLevelItemCount() == 0
    previous_point = previous_session.editor.objects_at(0, 0, 0)
    assert previous_point is not None
    assert previous_point[0] is original
    assert not game.dirty
