from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

import mapedit_gl as renderer
from test_core import write_game_fixture
from U6 import obj
from pu6e_qt.controller import EditorController


@pytest.fixture(scope="session")
def workbench_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def workbench(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    workbench_app: QApplication,
):
    import pu6e_qt.main_window as workbench_module

    class StubCanvas(QWidget):
        fatal_error = Signal(str)

        def __init__(self, controller: EditorController) -> None:
            super().__init__()
            self.controller = controller

        def zoom(self, factor: float) -> None:
            renderer.scale_factor *= factor

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "workbench")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    monkeypatch.setattr(workbench_module, "MapCanvas", StubCanvas)
    window = workbench_module.MainWindow(controller)
    yield window
    window.close()


def test_workbench_composes_native_docks_and_position_status(workbench) -> None:
    assert workbench.docks.stack_dock.windowTitle() == "Object stack"
    assert workbench.docks.inspector_dock.windowTitle() == "Object properties"
    assert workbench.docks.tile_dock.windowTitle() == "Tile library"
    assert workbench.docks.chunk_dock.windowTitle() == "Map chunk"
    assert workbench.docks.book_dock.windowTitle() == "Books"
    assert workbench.docks.minimap_dock.windowTitle() == "World map"

    workbench.controller.set_position(0x134, 0x16C, 0)

    assert "134" in workbench.location_label.text()
    assert "16c" in workbench.location_label.text()


def test_workbench_map_selection_updates_stack_and_object_properties(workbench) -> None:
    current = obj.default_object()
    obj.add_object_at(current, 5, 6, 0)

    workbench.controller.select_location(5, 6, 0)

    assert workbench.docks.stack.tree.topLevelItemCount() == 1
    assert workbench.docks.inspector.quality.value() == current.quality


def test_workbench_overlay_action_matches_renderer_state(workbench) -> None:
    action = workbench.findChild(type(workbench.actions.terrain), "toggle-display_grid")
    assert action is not None

    action.setChecked(True)
    assert renderer.display_grid == 1

    action.setChecked(False)
    assert renderer.display_grid == 0


def test_workbench_tile_selection_emits_one_controller_update(workbench) -> None:
    selected: list[int] = []
    workbench.controller.selected_tile_changed.connect(selected.append)

    workbench.docks.tiles.select_tile(12)

    assert selected == [12]


def test_stack_copy_shortcut_wins_over_chunk_dock_shortcut(workbench) -> None:
    current = obj.default_object()
    obj.add_object_at(current, 5, 6, 0)
    workbench.controller.select_location(5, 6, 0)
    point = obj.objects_at(5, 6, 0)
    assert point is not None

    QTest.keyClick(workbench.docks.stack.tree, Qt.Key.Key_C)
    QTest.keyClick(workbench.docks.stack.tree, Qt.Key.Key_V)

    assert len(point) == 2
    assert point[1] is not current


def test_workbench_reports_an_unsupported_opengl_context(
    workbench, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QMessageBox

    errors: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "critical",
        lambda parent, title, message: errors.append(message),
    )

    workbench.canvas.fatal_error.emit("OpenGL ES does not support this renderer")

    assert errors == ["OpenGL ES does not support this renderer"]
    assert "OpenGL" in workbench.statusBar().currentMessage()
