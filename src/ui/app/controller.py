from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QSignalBlocker, Signal
from PySide6.QtGui import QUndoStack

from game.models.coordinates import adjust_coords_for_level
from game.models.objects import WorldObject
from game.services.loader import WorldLoader
from game.services.saver import WorldSaver
from game.services.session import WorldSession
from ui.app.commands import ChunkSetCommand, TilePaintCommand
from ui.rendering.camera import CameraState
from ui.rendering.options import RenderOptions


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


class SessionNotLoadedError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Load a game before accessing its world")


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
    session_changed = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._update_clean_state)
        self.camera = CameraState()
        self.render_options = RenderOptions()
        self.loader = WorldLoader()
        self.saver = WorldSaver()
        self._session: WorldSession | None = None
        self.selected_location: tuple[int, int, int] | None = None
        self.selected_object: WorldObject | None = None
        self._selected_tile = 0
        self._terrain_mode = False
        self._manual_dirty = False
        self.dirty = False

    @property
    def session(self) -> WorldSession:
        if self._session is None:
            raise SessionNotLoadedError()
        return self._session

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    @property
    def position(self) -> tuple[int, int, int]:
        return self.camera.position

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
        self.replace_session(self.loader.load(directory, game))

    def replace_session(self, session: WorldSession) -> None:
        self._session = session
        self._manual_dirty = False
        with QSignalBlocker(self.undo_stack):
            self.undo_stack.clear()
        self.selected_location = None
        self.selected_object = None
        self._selected_tile = 0
        self.dirty = False
        self.camera.set_position(0, 0, 0)
        self.session_changed.emit()
        self.selected_object_changed.emit(None)
        self.selected_tile_changed.emit(0)
        self.position_changed.emit(*self.position)
        self.changed.emit(False)

    def save(self) -> None:
        self.saver.save(self.session)
        self._manual_dirty = False
        self.undo_stack.setClean()
        self.dirty = False
        self.changed.emit(False)
        self.saved.emit()

    def set_position(self, x: int, y: int, z: int) -> None:
        self.camera.set_position(x, y, z)
        self.position_changed.emit(*self.position)

    def select_location(self, x: int, y: int, z: int) -> None:
        self.selected_location = (x, y, z)
        self.location_selected.emit(x, y, z)

    def change_level(self, new_z: int, quality: int = 0) -> None:
        x, y, z = self.position
        destination = adjust_coords_for_level(x, y, z, new_z, quality)
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
        self.undo_stack.push(TilePaintCommand(self.session.editor, tile_id, x, y, z))

    def set_chunk(self, chunk_id: int, x: int, y: int, z: int) -> None:
        self.undo_stack.push(ChunkSetCommand(self.session.editor, chunk_id, x, y, z))

    def select_object(self, item: WorldObject | None) -> None:
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
        self.session.editor.mark_object_changed(x, y, z)
        self.mark_changed()

    def mark_object_changed(self, item: WorldObject) -> None:
        location = self.selected_location
        if location is None:
            self.mark_dirty(item.x, item.y, item.z)
            return
        self.mark_dirty(*location)

    def update_object_property(self, item: WorldObject, name: str, value: int) -> None:
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

    def move_object(self, item: WorldObject, x: int, y: int, z: int) -> bool:
        if not self.session.editor.move_object(item, x, y, z):
            return False
        self.select_object(item)
        self.mark_changed()
        return True

    def copy_object(self, item: WorldObject, x: int, y: int, z: int) -> WorldObject | None:
        copy = self.session.editor.copy_object(item, x, y, z)
        if copy is None:
            return None
        self.select_object(copy)
        self.mark_changed()
        return copy
