from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt

import mapedit_gl as renderer
from test_core import write_game_fixture
from U6 import Map, U6util, obj
from pu6e_qt.controller import EditorController


@pytest.fixture
def map_controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> EditorController:
    game_directory = tmp_path / "world"
    write_game_fixture(game_directory, "fp", "map interactions")
    controller = EditorController()
    controller.load_game(game_directory, "fp")
    monkeypatch.setattr(renderer, "display_objects", 1)
    return controller


@pytest.mark.parametrize(
    ("key", "expected"),
    (
        (Qt.Key.Key_Left, (-1, 0)),
        (Qt.Key.Key_Right, (1, 0)),
        (Qt.Key.Key_Up, (0, -1)),
        (Qt.Key.Key_Down, (0, 1)),
    ),
)
def test_arrow_navigation_moves_one_tile(key: Qt.Key, expected: tuple[int, int]) -> None:
    from pu6e_qt.map_navigation import navigation_action

    action = navigation_action(key.value, keypad=False)

    assert action is not None
    assert (action.dx, action.dy) == expected


@pytest.mark.parametrize(
    ("key", "expected"),
    (
        (Qt.Key.Key_1, (-8, 8)),
        (Qt.Key.Key_2, (0, 8)),
        (Qt.Key.Key_3, (8, 8)),
        (Qt.Key.Key_4, (-8, 0)),
        (Qt.Key.Key_6, (8, 0)),
        (Qt.Key.Key_7, (-8, -8)),
        (Qt.Key.Key_8, (0, -8)),
        (Qt.Key.Key_9, (8, -8)),
    ),
)
def test_keypad_navigation_moves_entire_chunks(
    key: Qt.Key,
    expected: tuple[int, int],
) -> None:
    from pu6e_qt.map_navigation import navigation_action

    action = navigation_action(key.value, keypad=True)

    assert action is not None
    assert (action.dx, action.dy) == expected


@pytest.mark.parametrize(
    ("key", "expected"),
    ((Qt.Key.Key_0, -1), (Qt.Key.Key_5, 1)),
)
def test_keypad_level_navigation_selects_adjacent_level(
    key: Qt.Key,
    expected: int,
) -> None:
    from pu6e_qt.map_navigation import navigation_action

    action = navigation_action(key.value, keypad=True)

    assert action is not None
    assert action.level_delta == expected


@pytest.mark.parametrize(
    ("key", "expected"),
    ((Qt.Key.Key_Plus, 2.0), (Qt.Key.Key_Equal, 2.0), (Qt.Key.Key_Minus, 0.5)),
)
def test_zoom_navigation_uses_legacy_scale_factors(key: Qt.Key, expected: float) -> None:
    from pu6e_qt.map_navigation import navigation_action

    action = navigation_action(key.value, keypad=False)

    assert action is not None
    assert action.zoom_factor == expected


def test_regular_number_keys_do_not_trigger_chunk_navigation() -> None:
    from pu6e_qt.map_navigation import navigation_action

    assert navigation_action(Qt.Key.Key_7.value, keypad=False) is None


def test_opengl_format_requests_desktop_legacy_compatibility() -> None:
    from PySide6.QtGui import QSurfaceFormat

    from pu6e_qt.canvas import configure_opengl_format

    surface_format = configure_opengl_format()

    assert surface_format.renderableType() == QSurfaceFormat.RenderableType.OpenGL
    assert surface_format.profile() == QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile
    assert surface_format.depthBufferSize() >= 16


def test_object_drag_preserves_identity_and_original_anchor_offset(
    map_controller: EditorController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    current = obj.default_object()
    obj.add_object_at(current, 10, 10, 0)
    monkeypatch.setattr(U6util, "lookable_at", lambda x, y, z: current)
    interaction = MapInteraction(map_controller)
    interaction.press_left(9, 9, 0)

    interaction.release_left(20, 20, 0, shift=False, control=False)

    destination = obj.objects_at(21, 21, 0)
    assert destination is not None
    assert destination[-1] is current


def test_control_drag_creates_distinct_object_clone(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    original = obj.default_object()
    obj.add_object_at(original, 4, 4, 0)
    interaction = MapInteraction(map_controller)
    interaction.press_left(4, 4, 0)

    interaction.release_left(7, 7, 0, shift=False, control=True)

    source = obj.objects_at(4, 4, 0)
    destination = obj.objects_at(7, 7, 0)
    assert source is not None and source[-1] is original
    assert destination is not None and destination[-1] is not original


def test_shift_drag_assigns_source_map_chunk(map_controller: EditorController) -> None:
    from pu6e_qt.map_input import MapInteraction

    Map.chunks.append(list(Map.chunks[0]))
    Map.set_chunk_at(1, 0, 0, 0)
    interaction = MapInteraction(map_controller)
    interaction.press_left(1, 1, 0)

    interaction.release_left(9, 1, 0, shift=True, control=False)

    assert Map.world_to_chunk_num(9, 1, 0)[0] == 1


def test_disabled_terrain_drag_does_not_change_destination(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    Map.set_maptile_at(7, 1, 1, 0)
    interaction = MapInteraction(map_controller)
    interaction.press_left(1, 1, 0)

    interaction.release_left(2, 2, 0, shift=False, control=False)

    assert Map.maptile_at(2, 2, 0) == 0


def test_enabled_terrain_drag_copies_source_background_tile(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    Map.set_maptile_at(7, 1, 1, 0)
    map_controller.terrain_mode = True
    interaction = MapInteraction(map_controller)
    interaction.press_left(1, 1, 0)

    interaction.release_left(2, 2, 0, shift=False, control=False)

    assert Map.maptile_at(2, 2, 0) == 7


def test_right_drag_paints_each_entered_background_tile(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    map_controller.selected_tile = 13
    interaction = MapInteraction(map_controller)
    interaction.press_right(1, 1, 0)

    interaction.drag_right(2, 1, 0)

    assert (Map.maptile_at(1, 1, 0), Map.maptile_at(2, 1, 0)) == (13, 13)


def test_right_paint_rejects_object_only_tile_ids(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    map_controller.selected_tile = 256
    interaction = MapInteraction(map_controller)

    painted = interaction.press_right(1, 1, 0)

    assert painted is False
    assert Map.maptile_at(1, 1, 0) == 0


def test_clicking_empty_location_does_not_create_world_point(
    map_controller: EditorController,
) -> None:
    from pu6e_qt.map_input import MapInteraction

    interaction = MapInteraction(map_controller)
    interaction.press_left(1, 1, 0)

    interaction.release_left(1, 1, 0, shift=False, control=False)

    assert obj.objects_at(1, 1, 0) is None
