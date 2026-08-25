from __future__ import annotations

from collections.abc import Sequence
from typing import Final

import numpy as np
from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

import mapedit_gl as render
from U6 import Map, tile
from pu6e_qt.controller import EditorController
from pu6e_qt.theme import THEME

MINIMAP_EDGE: Final = 256
SURFACE_WORLD_EDGE: Final = 1024
DUNGEON_WORLD_EDGE: Final = 256
TILE_EDGE: Final = 16
BACKGROUND_TILE_COUNT: Final = 256

RGB = tuple[int, int, int]


def render_world_minimap(level: int, palette: Sequence[RGB]) -> QImage:
    chunks = np.asarray(Map.chunks, dtype=np.uint8).reshape(-1, 8, 8)
    if level == 0:
        superchunks = np.asarray(Map.map[:64], dtype=np.intp).reshape(8, 8, 16, 16)
        chunk_grid = superchunks.transpose(0, 2, 1, 3).reshape(128, 128)
        world_tiles = chunks[chunk_grid][:, :, ::4, ::4]
        map_tiles = world_tiles.transpose(0, 2, 1, 3).reshape(MINIMAP_EDGE, MINIMAP_EDGE)
    else:
        chunk_grid = np.asarray(Map.map[63 + level], dtype=np.intp).reshape(32, 32)
        world_tiles = chunks[chunk_grid]
        map_tiles = world_tiles.transpose(0, 2, 1, 3).reshape(MINIMAP_EDGE, MINIMAP_EDGE)

    indexed_tiles = np.frombuffer(
        b"".join(tile.maptiles[:BACKGROUND_TILE_COUNT]),
        dtype=np.uint8,
    ).reshape(BACKGROUND_TILE_COUNT, TILE_EDGE * TILE_EDGE)
    center_pixel = (TILE_EDGE // 2) * TILE_EDGE + TILE_EDGE // 2
    center_indices = indexed_tiles[:, center_pixel].copy()
    animation_count = tile.anim["numtiles"]
    animated_tiles = tile.anim["tiles"][:animation_count]
    first_frames = tile.anim["first_frame"][:animation_count]
    for source_tile, frame_tile in zip(animated_tiles, first_frames, strict=True):
        if 0 <= source_tile < BACKGROUND_TILE_COUNT:
            center_indices[source_tile] = tile.maptiles[frame_tile][center_pixel]
    tile_colors = np.asarray(palette, dtype=np.uint8)[center_indices]
    colors = np.ascontiguousarray(tile_colors[map_tiles])
    return QImage(
        colors.tobytes(),
        MINIMAP_EDGE,
        MINIMAP_EDGE,
        MINIMAP_EDGE * 3,
        QImage.Format.Format_RGB888,
    ).copy()


class WorldMinimap(QWidget):
    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.position = controller.position
        self.image = QImage()
        self.setMinimumSize(180, 200)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setAccessibleName("Interactive world overview map")
        self.setToolTip("Click or drag the overview to navigate the world")
        self._rebuild()
        self.controller.position_changed.connect(self._position_changed)
        self.controller.changed.connect(self._world_changed)

    @property
    def world_extent(self) -> int:
        return SURFACE_WORLD_EDGE if self.position[2] == 0 else DUNGEON_WORLD_EDGE

    def sizeHint(self) -> QSize:
        return QSize(256, 284)

    def map_rect(self) -> QRect:
        padding = THEME.space_2
        edge = max(1, min(self.width() - padding * 2, self.height() - padding * 4))
        return QRect((self.width() - edge) // 2, padding, edge, edge)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.map_rect()
        painter.fillRect(self.rect(), QColor(THEME.surface_canvas))
        painter.drawImage(rect, self.image)
        painter.setPen(QPen(QColor(THEME.border_default), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        self._draw_viewport(painter, rect)

        x, y, z = self.position
        label = "SURFACE" if z == 0 else f"LEVEL {z}"
        painter.setPen(QColor(THEME.text_secondary))
        footer = QRect(rect.x(), rect.bottom() + THEME.space_1, rect.width(), 20)
        painter.drawText(footer, Qt.AlignmentFlag.AlignCenter, f"{label}  ·  {x:03x}, {y:03x}")
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._navigate(event.position())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._navigate(event.position())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _draw_viewport(self, painter: QPainter, rect: QRect) -> None:
        x, y, _ = self.position
        scale = rect.width() / self.world_extent
        center_x = rect.x() + round(x * scale)
        center_y = rect.y() + round(y * scale)
        half_x, half_y = render.center_offset
        width = max(7, round(half_x * 2 * scale))
        height = max(7, round(half_y * 2 * scale))
        viewport = QRect(center_x - width // 2, center_y - height // 2, width, height)
        painter.setPen(QPen(QColor(THEME.accent_primary), 2))
        painter.drawRect(viewport)
        painter.fillRect(center_x - 1, center_y - 1, 3, 3, QColor(THEME.text_primary))

    def _navigate(self, pointer: QPointF) -> None:
        rect = self.map_rect()
        if not rect.contains(pointer.toPoint()):
            return
        x_ratio = (pointer.x() - rect.x()) / rect.width()
        y_ratio = (pointer.y() - rect.y()) / rect.height()
        x = min(self.world_extent - 1, max(0, int(x_ratio * self.world_extent)))
        y = min(self.world_extent - 1, max(0, int(y_ratio * self.world_extent)))
        self.controller.set_position(x, y, self.position[2])

    def _position_changed(self, x: int, y: int, z: int) -> None:
        level_changed = z != self.position[2]
        self.position = (x, y, z)
        if level_changed:
            self._rebuild()
        self.update()

    def _world_changed(self, dirty: bool) -> None:
        self._rebuild()
        self.update()

    def _rebuild(self) -> None:
        palette = self.controller.palette
        if palette is not None:
            self.image = render_world_minimap(self.position[2], palette.pal)
