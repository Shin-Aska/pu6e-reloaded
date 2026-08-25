from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Final, Protocol

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QAbstractItemView, QLineEdit, QListWidget, QListWidgetItem, QLabel, QVBoxLayout, QWidget

from U6 import look, pal, tile

TileId = int
RGB = tuple[int, int, int]
PaletteEntries = Sequence[RGB]
TileNameLookup = Callable[[TileId], str | None]

TILE_EDGE: Final = 16
TILE_PIXELS: Final = TILE_EDGE * TILE_EDGE
BACKGROUND_TILE_LIMIT: Final = 256
GAME_TILE_LIMIT: Final = 2048


class IntegerSignal(Protocol):
    def connect(self, slot: Callable[[int], None], /) -> None:
        pass


class TileSelectionController(Protocol):
    selected_tile: TileId
    selected_tile_changed: IntegerSignal
    palette: pal.pal | None

    def set_selected_tile(self, tile_id: TileId, /) -> None:
        pass


def indexed_tile_image(indexed_pixels: bytes, palette: PaletteEntries) -> QImage | None:
    if len(indexed_pixels) != TILE_PIXELS or len(palette) < 256:
        return None

    rgba = bytearray(TILE_PIXELS * 4)
    for pixel_offset, color_index in enumerate(indexed_pixels):
        red, green, blue = palette[color_index]
        rgba_offset = pixel_offset * 4
        rgba[rgba_offset:rgba_offset + 4] = bytes((red, green, blue, 0 if color_index == 255 else 255))
    return QImage(bytes(rgba), TILE_EDGE, TILE_EDGE, TILE_EDGE * 4, QImage.Format.Format_RGBA8888).copy()


def tile_icon(indexed_pixels: bytes, palette: PaletteEntries) -> QIcon | None:
    image = indexed_tile_image(indexed_pixels, palette)
    if image is None:
        return None
    return QIcon(QPixmap.fromImage(image))


class TileBrowser(QWidget):
    """Tile library whose selected ID is synchronized with an editor controller.

    Pass a controller exposing ``selected_tile``, ``set_selected_tile`` and
    ``selected_tile_changed``.  Tile IDs 256–2047 are legitimate object tiles,
    but their selected summary explicitly warns that a map background only has
    the 8-bit range 0–255.
    """

    tile_selected = Signal(int)

    def __init__(
        self,
        controller: TileSelectionController | None = None,
        parent: QWidget | None = None,
        *,
        palette: PaletteEntries | None = None,
        tiles: Sequence[bytes] | None = None,
        name_for_tile: TileNameLookup = look.get_obj_name,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        controller_palette = (
            controller.palette.pal
            if controller is not None and controller.palette is not None
            else None
        )
        self._palette = palette if palette is not None else controller_palette
        self._tiles = tiles
        self._name_for_tile = name_for_tile
        self._selected_tile: TileId | None = None

        self.setAccessibleName("Tile library")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.search = QLineEdit(self)
        self.search.setAccessibleName("Search tiles")
        self.search.setPlaceholderText("Search tile ID or name")
        layout.addWidget(self.search)
        self.grid = QListWidget(self)
        self.grid.setAccessibleName("Tile grid")
        self.grid.setViewMode(QListWidget.ViewMode.IconMode)
        self.grid.setFlow(QListWidget.Flow.LeftToRight)
        self.grid.setWrapping(True)
        self.grid.setMovement(QListWidget.Movement.Static)
        self.grid.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.grid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.grid.setIconSize(QSize(32, 32))
        self.grid.setGridSize(QSize(160, 64))
        layout.addWidget(self.grid, 1)
        self.summary = QLabel("No tile selected", self)
        self.summary.setAccessibleName("Selected tile summary")
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

        self.search.textChanged.connect(self._apply_filter)
        self.grid.currentItemChanged.connect(self._grid_selection_changed)
        if controller is not None:
            controller.selected_tile_changed.connect(self.select_tile)
        self.reload_tiles()
        if controller is not None:
            self.select_tile(controller.selected_tile)

    def reload_tiles(
        self,
        *,
        palette: PaletteEntries | None = None,
        tiles: Sequence[bytes] | None = None,
    ) -> None:
        if palette is not None:
            self._palette = palette
        if tiles is not None:
            self._tiles = tiles
        self.grid.clear()
        current_palette = self._palette
        current_tiles = self._tiles if self._tiles is not None else tile.maptiles
        if current_palette is None:
            self.summary.setText("Tile graphics unavailable: no palette is loaded")
            return
        for tile_id, indexed_pixels in enumerate(current_tiles[:GAME_TILE_LIMIT]):
            icon = tile_icon(indexed_pixels, current_palette)
            if icon is not None:
                self._add_tile_item(tile_id, icon)
        self._apply_filter(self.search.text())
        if self._selected_tile is not None:
            self.select_tile(self._selected_tile)

    def selected_tile(self) -> TileId | None:
        return self._selected_tile

    def select_tile(self, tile_id: TileId) -> None:
        item = self._item_for_tile(tile_id)
        if item is None:
            return
        self.grid.setCurrentItem(item)
        self.grid.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _add_tile_item(self, tile_id: TileId, icon: QIcon) -> None:
        name = self._name_for_tile(tile_id) or "Unnamed tile"
        item = QListWidgetItem(icon, f"{tile_id:04d} · {name}")
        item.setData(Qt.ItemDataRole.UserRole, tile_id)
        item.setToolTip(f"Tile {tile_id}: {name}")
        self.grid.addItem(item)

    def _item_for_tile(self, tile_id: TileId) -> QListWidgetItem | None:
        if tile_id < 0:
            return None
        for row in range(self.grid.count()):
            item = self.grid.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == tile_id:
                return item
        return None

    def _apply_filter(self, query: str) -> None:
        normalized_query = query.casefold().strip()
        for row in range(self.grid.count()):
            item = self.grid.item(row)
            item.setHidden(normalized_query not in item.text().casefold())

    def _grid_selection_changed(self, current: QListWidgetItem | None, _: QListWidgetItem | None) -> None:
        if current is None:
            return
        tile_id = current.data(Qt.ItemDataRole.UserRole)
        if not isinstance(tile_id, int):
            return
        self._selected_tile = tile_id
        name = self._name_for_tile(tile_id) or "Unnamed tile"
        background_note = (
            "Background-safe tile"
            if tile_id < BACKGROUND_TILE_LIMIT
            else "Object tile — not valid as map background"
        )
        self.summary.setText(f"Tile {tile_id}: {name}. {background_note}.")
        if self._controller is not None:
            self._controller.set_selected_tile(tile_id)
        self.tile_selected.emit(tile_id)
