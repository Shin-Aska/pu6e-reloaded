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
from pu6e_qt.renderer_settings import RendererMode, RendererRuntime


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
        zoom_changed = Signal(float)

        def __init__(self, controller: EditorController) -> None:
            super().__init__()
            self.controller = controller

        def zoom(self, factor: float) -> None:
            renderer.scale_factor *= factor
            self.zoom_changed.emit(renderer.scale_factor)

    game_dir = tmp_path / "fp"
    write_game_fixture(game_dir, "fp", "workbench")
    controller = EditorController()
    controller.load_game(game_dir, "fp")
    renderer.scale_factor = 1.0
    monkeypatch.setattr(workbench_module, "MapCanvas", StubCanvas)
    window = workbench_module.MainWindow(
        controller,
        RendererRuntime(RendererMode.OPENGL),
    )
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


def test_workbench_title_identifies_the_active_renderer(workbench) -> None:
    # Given: the workbench was opened under the resolved OpenGL runtime.
    # When: the native window title is read.
    title = workbench.windowTitle()

    # Then: users can see the active backend throughout the editing session.
    assert title.endswith("[Renderer: OpenGL]")


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


def test_toolbar_uses_icon_only_shortcuts_with_undo_and_redo(workbench) -> None:
    toolbar = workbench.actions.toolbar
    named_actions = [action for action in toolbar.actions() if not action.isSeparator()]

    assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
    assert {"Save world", "Undo", "Redo", "Zoom in", "Zoom out"}.issubset(
        {action.text() for action in named_actions}
    )
    assert all(not action.icon().isNull() for action in named_actions if action.text())


def test_zoom_indicators_follow_toolbar_actions_immediately(workbench) -> None:
    workbench.actions.zoom_out.trigger()

    assert workbench.zoom_label.text() == "50%"
    assert workbench.actions.zoom_selector.currentText() == "50%"


def test_zoom_selector_applies_an_explicit_percentage(workbench) -> None:
    workbench.actions.zoom_selector.setCurrentText("200%")

    assert renderer.scale_factor == 2.0
    assert workbench.zoom_label.text() == "200%"


def test_zoom_selector_only_offers_supported_percentages(workbench) -> None:
    selector = workbench.actions.zoom_selector

    percentages = tuple(selector.itemText(index) for index in range(selector.count()))

    assert percentages == ("25%", "50%", "100%", "200%", "400%")


@pytest.mark.parametrize(
    "zoom_scenario",
    ((0.25, True, False), (1.0, True, True), (4.0, False, True)),
)
def test_zoom_actions_disable_at_the_supported_limits(
    workbench,
    zoom_scenario: tuple[float, bool, bool],
) -> None:
    scale, zoom_in_enabled, zoom_out_enabled = zoom_scenario
    renderer.scale_factor = scale

    workbench.canvas.zoom_changed.emit(scale)

    assert (workbench.actions.zoom_in.isEnabled(), workbench.actions.zoom_out.isEnabled()) == (
        zoom_in_enabled,
        zoom_out_enabled,
    )


def test_level_selector_jumps_directly_between_surface_and_underworld(workbench) -> None:
    workbench.controller.set_position(0x134, 0x16C, 0)

    workbench.actions.level_selector.setCurrentIndex(3)

    assert workbench.controller.position[2] == 3
    assert "Underworld 3" in workbench.actions.level_selector.currentText()


def test_level_selector_stays_synchronized_with_keyboard_navigation(workbench) -> None:
    workbench.controller.change_level(2)

    assert workbench.actions.level_selector.currentIndex() == 2


def test_quest_browser_tabs_with_object_stack_without_hiding_the_minimap(workbench) -> None:
    stack_tabs = workbench.tabifiedDockWidgets(workbench.docks.stack_dock)

    assert workbench.docks.quest_dock in stack_tabs
    assert workbench.docks.minimap_dock not in stack_tabs
