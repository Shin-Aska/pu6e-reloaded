from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoStack

import mapedit_gl as renderer
from U6 import Map, NPCs, obj, pal

from pu6e_qt.commands import ChunkSetCommand, TilePaintCommand


@dataclass(frozen=True, slots=True)
class InvalidBackgroundTileError(ValueError):
    tile_id: int

    def __str__(self) -> str:
        return f"background tile must be in 0..255, got {self.tile_id}"


@dataclass(frozen=True, slots=True)
class InvalidObjectPropertyError(ValueError):
    name: str

    def __str__(self) -> str:
        return f"unsupported editable object property: {self.name}"


class EditorController(QObject):
    """Mutable editor session state; mutations notify Qt consumers immediately."""

    position_changed = Signal(int, int, int)
    location_selected = Signal(int, int, int)
    selected_object_changed = Signal(object)
    changed = Signal(bool)
    saved = Signal()
    error = Signal(str)
    selected_tile_changed = Signal(int)
    terrain_mode_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._update_clean_state)
        self.position: tuple[int, int, int] = (0, 0, 0)
        self.selected_location: tuple[int, int, int] | None = None
        self.selected_object: obj.Obj | None = None
        self._selected_tile = 0
        self._terrain_mode = False
        self._manual_dirty = False
        self.dirty = False
        self.palette: pal.pal | None = None

    @property
    def selected_tile(self) -> int:
        return self._selected_tile

    @selected_tile.setter
    def selected_tile(self, tile_id: int) -> None:
        self._selected_tile = tile_id
        self.selected_tile_changed.emit(tile_id)

    @property
    def terrain_mode(self) -> bool:
        return self._terrain_mode

    @terrain_mode.setter
    def terrain_mode(self, enabled: bool) -> None:
        self._terrain_mode = enabled
        self.terrain_mode_changed.emit(enabled)

    def load_game(self, directory: Path, game: str) -> None:
        renderer.read_data(str(directory), game)
        self.palette = renderer.palette
        self._manual_dirty = False
        self.undo_stack.clear()
        self.dirty = False
        self.set_position(0, 0, 0)
        self.changed.emit(False)

    def save(self) -> None:
        obj.write_changes()
        NPCs.write()
        Map.write_changes()
        self._manual_dirty = False
        self.undo_stack.setClean()
        self.dirty = False
        self.changed.emit(False)
        self.saved.emit()

    def set_position(self, x: int, y: int, z: int) -> None:
        renderer.set_centered_coords(x, y, z)
        self.position = renderer.get_centered_coords()
        self.position_changed.emit(*self.position)

    def select_location(self, x: int, y: int, z: int) -> None:
        self.selected_location = (x, y, z)
        self.location_selected.emit(x, y, z)

    def change_level(self, new_z: int, quality: int = 0) -> None:
        x, y, z = self.position
        destination = Map.adjust_coords_for_level(x, y, z, new_z, quality)
        self.set_position(*destination)

    def set_selected_tile(self, tile_id: int) -> None:
        self.selected_tile = tile_id

    def select_tile(self, tile_id: int) -> None:
        self.set_selected_tile(tile_id)

    def set_terrain_mode(self, enabled: bool) -> None:
        self.terrain_mode = enabled

    def paint_tile(self, tile_id: int, x: int, y: int, z: int) -> None:
        if not 0 <= tile_id <= 255:
            raise InvalidBackgroundTileError(tile_id)
        self.undo_stack.push(TilePaintCommand(tile_id, x, y, z))

    def set_chunk(self, chunk_id: int, x: int, y: int, z: int) -> None:
        self.undo_stack.push(ChunkSetCommand(chunk_id, x, y, z))

    def select_object(self, item: obj.Obj | None) -> None:
        self.selected_object = item
        self.selected_object_changed.emit(item)

    def mark_changed(self) -> None:
        self._manual_dirty = True
        self.dirty = True
        self.changed.emit(True)

    def _update_clean_state(self, clean: bool) -> None:
        self.dirty = self._manual_dirty or not clean
        self.changed.emit(self.dirty)

    def mark_dirty(self, x: int, y: int, z: int) -> None:
        obj.updated_at(x, y, z)
        self.mark_changed()

    def mark_object_changed(self, item: obj.Obj) -> None:
        location = self.selected_location
        if location is None:
            self.mark_dirty(item.x, item.y, item.z)
            return
        self.mark_dirty(*location)

    def update_object_property(self, item: obj.Obj, name: str, value: int) -> None:
        updaters: dict[str, Callable[[int], None]] = {
            "quantity": lambda current: setattr(item, "quantity", current),
            "quality": lambda current: setattr(item, "quality", current),
            "status": lambda current: setattr(item, "status", current),
            "type": item.set_type,
            "frame": item.set_frame,
        }
        updater = updaters.get(name)
        if updater is None:
            raise InvalidObjectPropertyError(name)
        updater(value)
        self.mark_object_changed(item)

    def move_object(self, item: obj.Obj, x: int, y: int, z: int) -> bool:
        if not obj.remove_object_at(item, item.x, item.y, item.z):
            return False
        obj.add_object_at(item, x, y, z)
        self.select_object(item)
        self.mark_changed()
        return True

    def copy_object(self, item: obj.Obj, x: int, y: int, z: int) -> obj.Obj | None:
        copy = item.clone()
        if copy is None:
            return None
        obj.add_object_at(copy, x, y, z)
        self.select_object(copy)
        self.mark_changed()
        return copy
