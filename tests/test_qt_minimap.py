from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from game_fixtures import write_game_fixture
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from game.models.assets import AnimationData, Palette
from ui.app.controller import EditorController


@pytest.fixture(scope="session")
def minimap_app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def minimap_controller(tmp_path: Path, minimap_app: QApplication) -> EditorController:
    directory = tmp_path / "minimap"
    write_game_fixture(directory, "fp", "minimap")
    controller = EditorController()
    controller.load_game(directory, "fp")
    controller.set_position(100, 100, 0)
    return controller


def test_world_minimap_renders_surface_and_dungeon_at_fixed_resolution(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import render_world_minimap

    state = minimap_controller.session.state

    surface = render_world_minimap(state, 0)
    dungeon = render_world_minimap(state, 1)

    assert (surface.width(), surface.height()) == (256, 256)
    assert (dungeon.width(), dungeon.height()) == (256, 256)


def test_world_minimap_uses_actual_tile_palette_colors(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import render_world_minimap

    state = minimap_controller.session.state

    image = render_world_minimap(state, 0)

    assert image.pixelColor(0, 0).getRgb()[:3] == state.assets.palette.colors[0]


def test_minimap_resolves_transparent_animated_terrain_to_its_visible_frame(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import render_world_minimap

    state = minimap_controller.session.state
    colors = list(state.assets.palette.colors)
    colors[7] = (12, 34, 56)
    pixels = list(state.assets.tiles.pixels)
    pixels[0] = bytes((255,)) * 256
    pixels[1] = bytes((7,)) * 256
    state.assets = replace(
        state.assets,
        palette=Palette(tuple(colors)),
        tiles=replace(
            state.assets.tiles,
            pixels=tuple(pixels),
            animations=AnimationData(1, (0,), (1,), (0,), (0,)),
        ),
    )

    image = render_world_minimap(state, 0)

    assert image.pixelColor(0, 0).getRgb()[:3] == (12, 34, 56)


def test_minimap_click_navigates_the_surface_world(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)
    minimap.resize(256, 280)
    target = QPointF(minimap.map_rect().center())
    click = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        target,
        target,
        target,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    minimap.mousePressEvent(click)

    x, y, z = minimap_controller.position
    assert 500 <= x <= 524
    assert 500 <= y <= 524
    assert z == 0


def test_minimap_tracks_controller_position_and_level(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)

    minimap_controller.set_position(32, 48, 2)

    assert minimap.position == (32, 48, 2)
    assert minimap.world_extent == 256


def test_minimap_refreshes_after_a_terrain_edit(
    minimap_controller: EditorController,
) -> None:
    from ui.app.map.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)
    minimap_controller.session.editor.set_map_tile(1, 0, 0, 0)

    minimap_controller.changed.emit(True)

    assert not minimap.image.isNull()


def test_minimap_reloads_palette_when_controller_loads_another_game(
    minimap_controller: EditorController, tmp_path: Path,
) -> None:
    from ui.app.map.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)
    original_color = minimap.image.pixelColor(0, 0)
    directory = tmp_path / "second"
    write_game_fixture(directory, "fp", "second minimap")
    (directory / "u6pal").write_bytes(bytes((2,)) * 768)

    minimap_controller.load_game(directory, "fp")

    assert minimap.image.pixelColor(0, 0).getRgb()[:3] == (8, 8, 8)
    assert minimap.image.pixelColor(0, 0) != original_color


def test_minimaps_keep_their_own_session_when_another_controller_loads(
    minimap_controller: EditorController, tmp_path: Path,
) -> None:
    from ui.app.map.minimap import WorldMinimap

    original = WorldMinimap(minimap_controller)
    original_color = original.image.pixelColor(0, 0)
    directory = tmp_path / "independent"
    write_game_fixture(directory, "fp", "independent minimap")
    (directory / "u6pal").write_bytes(bytes((2,)) * 768)
    other_controller = EditorController()

    other_controller.load_game(directory, "fp")
    other = WorldMinimap(other_controller)
    minimap_controller.changed.emit(False)

    assert original.image.pixelColor(0, 0) == original_color
    assert other.image.pixelColor(0, 0).getRgb()[:3] == (8, 8, 8)
