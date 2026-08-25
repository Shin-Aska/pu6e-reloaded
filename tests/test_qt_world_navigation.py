from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import mapedit_gl as renderer
from test_core import write_game_fixture
from U6 import obj
from pu6e_qt.controller import EditorController


@pytest.fixture(scope="session")
def navigation_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def navigation_controller(tmp_path: Path, navigation_app: QApplication) -> EditorController:
    game_directory = tmp_path / "navigation"
    write_game_fixture(game_directory, "fp", "navigation")
    controller = EditorController()
    controller.load_game(game_directory, "fp")
    controller.set_position(100, 100, 0)
    renderer.scale_factor = 1.0
    renderer.display_objects = 1
    return controller


def mouse_event(
    event_type: QEvent.Type,
    x: float,
    y: float,
    button: Qt.MouseButton,
    buttons: Qt.MouseButton,
) -> QMouseEvent:
    position = QPointF(x, y)
    return QMouseEvent(
        event_type,
        position,
        position,
        position,
        button,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def test_middle_drag_pans_the_world_without_editing(
    navigation_controller: EditorController,
) -> None:
    from pu6e_qt.canvas import MapCanvas

    canvas = MapCanvas(navigation_controller)
    canvas.timer.stop()
    canvas.mousePressEvent(
        mouse_event(
            QEvent.Type.MouseButtonPress,
            80,
            80,
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.MiddleButton,
        )
    )

    canvas.mouseMoveEvent(
        mouse_event(
            QEvent.Type.MouseMove,
            112,
            96,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.MiddleButton,
        )
    )

    assert navigation_controller.position == (98, 99, 0)
    assert not navigation_controller.dirty


def test_left_drag_on_empty_background_pans_in_inspection_mode(
    navigation_controller: EditorController,
) -> None:
    from pu6e_qt.canvas import MapCanvas

    canvas = MapCanvas(navigation_controller)
    canvas.timer.stop()
    canvas.mousePressEvent(
        mouse_event(
            QEvent.Type.MouseButtonPress,
            80,
            80,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
        )
    )

    canvas.mouseMoveEvent(
        mouse_event(
            QEvent.Type.MouseMove,
            112,
            80,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
        )
    )

    assert navigation_controller.position == (98, 100, 0)
    assert not navigation_controller.dirty


def test_left_drag_on_an_object_remains_an_editing_gesture(
    navigation_controller: EditorController,
) -> None:
    from pu6e_qt.canvas import MapCanvas

    canvas = MapCanvas(navigation_controller)
    canvas.timer.stop()
    x, y, z = canvas._world_at(QPointF(80, 80))
    current = obj.default_object()
    obj.add_object_at(current, x, y, z)
    original_center = navigation_controller.position
    canvas.mousePressEvent(
        mouse_event(
            QEvent.Type.MouseButtonPress,
            80,
            80,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
        )
    )

    canvas.mouseMoveEvent(
        mouse_event(
            QEvent.Type.MouseMove,
            112,
            80,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
        )
    )

    assert navigation_controller.position == original_center


def test_terrain_mode_preserves_background_drag_for_editing(
    navigation_controller: EditorController,
) -> None:
    from pu6e_qt.canvas import MapCanvas

    canvas = MapCanvas(navigation_controller)
    canvas.timer.stop()
    navigation_controller.terrain_mode = True
    canvas.mousePressEvent(
        mouse_event(
            QEvent.Type.MouseButtonPress,
            80,
            80,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
        )
    )

    canvas.mouseMoveEvent(
        mouse_event(
            QEvent.Type.MouseMove,
            112,
            80,
            Qt.MouseButton.NoButton,
            Qt.MouseButton.LeftButton,
        )
    )

    assert navigation_controller.position == (100, 100, 0)


@pytest.mark.parametrize(
    "zoom_scenario",
    ((0.25, 0.5, 0.25), (0.3, 0.5, 0.25), (3.0, 2.0, 4.0), (4.0, 2.0, 4.0)),
)
def test_map_zoom_stays_between_twenty_five_and_four_hundred_percent(
    navigation_controller: EditorController,
    zoom_scenario: tuple[float, float, float],
) -> None:
    from pu6e_qt.canvas import MapCanvas

    initial_scale, factor, expected_scale = zoom_scenario
    renderer.scale_factor = initial_scale
    canvas = MapCanvas(navigation_controller)
    canvas.timer.stop()

    canvas.zoom(factor)

    assert renderer.scale_factor == expected_scale
