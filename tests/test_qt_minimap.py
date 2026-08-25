from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from test_core import write_game_fixture
from U6 import Map, tile
from pu6e_qt.controller import EditorController


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
    from pu6e_qt.minimap import render_world_minimap

    palette = minimap_controller.palette
    assert palette is not None

    surface = render_world_minimap(0, palette.pal)
    dungeon = render_world_minimap(1, palette.pal)

    assert (surface.width(), surface.height()) == (256, 256)
    assert (dungeon.width(), dungeon.height()) == (256, 256)


def test_world_minimap_uses_actual_tile_palette_colors(
    minimap_controller: EditorController,
) -> None:
    from pu6e_qt.minimap import render_world_minimap

    palette = minimap_controller.palette
    assert palette is not None

    image = render_world_minimap(0, palette.pal)

    assert image.pixelColor(0, 0).getRgb()[:3] == palette.pal[0]


def test_minimap_resolves_transparent_animated_terrain_to_its_visible_frame(
    minimap_controller: EditorController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pu6e_qt.minimap import render_world_minimap

    palette = minimap_controller.palette
    assert palette is not None
    palette.pal[7] = (12, 34, 56)
    tile.maptiles[0] = bytes((255,)) * 256
    tile.maptiles[1] = bytes((7,)) * 256
    monkeypatch.setitem(tile.anim, "numtiles", 1)
    monkeypatch.setitem(tile.anim, "tiles", (0,))
    monkeypatch.setitem(tile.anim, "first_frame", (1,))

    image = render_world_minimap(0, palette.pal)

    assert image.pixelColor(0, 0).getRgb()[:3] == (12, 34, 56)


def test_minimap_click_navigates_the_surface_world(
    minimap_controller: EditorController,
) -> None:
    from pu6e_qt.minimap import WorldMinimap

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
    from pu6e_qt.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)

    minimap_controller.set_position(32, 48, 2)

    assert minimap.position == (32, 48, 2)
    assert minimap.world_extent == 256


def test_minimap_refreshes_after_a_terrain_edit(
    minimap_controller: EditorController,
) -> None:
    from pu6e_qt.minimap import WorldMinimap

    minimap = WorldMinimap(minimap_controller)
    Map.set_maptile_at(1, 0, 0, 0)

    minimap_controller.changed.emit(True)

    assert not minimap.image.isNull()
