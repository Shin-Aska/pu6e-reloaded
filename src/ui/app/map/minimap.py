from __future__ import annotations

from typing import Final

import numpy as np
from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from game.models.world import WorldState
from ui.app.controller import EditorController
from ui.app.map.levels import WORLD_LEVELS
from ui.shared.theme import THEME

MINIMAP_EDGE: Final = 256
SURFACE_WORLD_EDGE: Final = 1024
DUNGEON_WORLD_EDGE: Final = 256
TILE_EDGE: Final = 16
BACKGROUND_TILE_COUNT: Final = 256
FOOTER_HEIGHT: Final = 40

def render_world_minimap(state: WorldState, level: int) -> QImage:
    chunks = np.asarray(state.terrain.chunks, dtype=np.uint8).reshape(-1, 8, 8)
    if level == 0:
        superchunks = np.asarray(state.terrain.superchunks[:64], dtype=np.intp).reshape(8, 8, 16, 16)
        chunk_grid = superchunks.transpose(0, 2, 1, 3).reshape(128, 128)
        world_tiles = chunks[chunk_grid][:, :, ::4, ::4]
        map_tiles = world_tiles.transpose(0, 2, 1, 3).reshape(MINIMAP_EDGE, MINIMAP_EDGE)
    else:
        chunk_grid = np.asarray(state.terrain.superchunks[63 + level], dtype=np.intp).reshape(32, 32)
        world_tiles = chunks[chunk_grid]
        map_tiles = world_tiles.transpose(0, 2, 1, 3).reshape(MINIMAP_EDGE, MINIMAP_EDGE)

    indexed_tiles = np.frombuffer(
        b"".join(state.assets.tiles.pixels[:BACKGROUND_TILE_COUNT]),
        dtype=np.uint8,
    ).reshape(BACKGROUND_TILE_COUNT, TILE_EDGE * TILE_EDGE)
    center_pixel = (TILE_EDGE // 2) * TILE_EDGE + TILE_EDGE // 2
    center_indices = indexed_tiles[:, center_pixel].copy()
    animation = state.assets.tiles.animations
    animation_count = animation.num_tiles
    animated_tiles = animation.tiles[:animation_count]
    first_frames = animation.first_frames[:animation_count]
    for source_tile, frame_tile in zip(animated_tiles, first_frames, strict=True):
        if 0 <= source_tile < BACKGROUND_TILE_COUNT:
            center_indices[source_tile] = state.assets.tiles.pixels[frame_tile][center_pixel]
    tile_colors = np.asarray(state.assets.palette.colors, dtype=np.uint8)[center_indices]
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
        self.controller.session_changed.connect(self._session_changed)

    @property
    def world_extent(self) -> int:
        return SURFACE_WORLD_EDGE if self.position[2] == 0 else DUNGEON_WORLD_EDGE

    def sizeHint(self) -> QSize:
        return QSize(256, 308)

    def map_rect(self) -> QRect:
        padding = THEME.space_2
        edge = max(1, min(self.width() - padding * 2, self.height() - padding * 3 - FOOTER_HEIGHT))
        return QRect((self.width() - edge) // 2, padding, edge, edge)

    @property
    def level_name(self) -> str:
        if not self.controller.is_loaded:
            return "World map"
        game = self.controller.session.state.game_type
        return WORLD_LEVELS[game][self.position[2]].label

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.map_rect()
        painter.fillRect(self.rect(), QColor(THEME.surface_canvas))
        painter.drawImage(rect, self.image)
        painter.setPen(QPen(QColor(THEME.border_default), 1))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        self._draw_viewport(painter, rect)

        x, y, z = self.position
        painter.setPen(QColor(THEME.text_secondary))
        footer = QRect(
            THEME.space_2, rect.bottom() + THEME.space_1,
            self.width() - THEME.space_2 * 2, 20,
        )
        label = painter.fontMetrics().elidedText(
            self.level_name, Qt.TextElideMode.ElideRight, footer.width()
        )
        painter.drawText(footer, Qt.AlignmentFlag.AlignCenter, label)
        painter.drawText(
            footer.translated(0, 20), Qt.AlignmentFlag.AlignCenter,
            f"{x:03x}, {y:03x} · Z {z}",
        )
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
        half_x, half_y = self.controller.camera.center_offset
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

    def _session_changed(self) -> None:
        self.position = self.controller.position
        self._rebuild()
        self.update()

    def _rebuild(self) -> None:
        self.setToolTip(f"{self.level_name} · Click or drag the overview to navigate the world")
        self.setAccessibleDescription(f"{self.level_name}, map slot {self.position[2]}")
        self.image = (
            render_world_minimap(self.controller.session.state, self.position[2])
            if self.controller.is_loaded
            else QImage()
        )
