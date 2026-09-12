from __future__ import annotations

from PySide6.QtGui import QUndoCommand

from pu6e_core.services.editor import WorldEditor


class TilePaintCommand(QUndoCommand):
    def __init__(
        self,
        editor: WorldEditor,
        tile_id: int,
        x: int,
        y: int,
        z: int,
    ) -> None:
        super().__init__("Paint terrain")
        self._editor = editor
        self._tile_id = tile_id
        self._x = x
        self._y = y
        self._z = z
        self._previous_tile = editor.map_tile_at(x, y, z)

    def redo(self) -> None:
        self._editor.set_map_tile(self._tile_id, self._x, self._y, self._z)

    def undo(self) -> None:
        self._editor.set_map_tile(self._previous_tile, self._x, self._y, self._z)


class ChunkSetCommand(QUndoCommand):
    def __init__(
        self,
        editor: WorldEditor,
        chunk_id: int,
        x: int,
        y: int,
        z: int,
    ) -> None:
        super().__init__("Set map chunk")
        self._editor = editor
        self._chunk_id = chunk_id
        self._x = x
        self._y = y
        self._z = z
        self._previous_chunk = editor.chunk_at(x, y, z)[0]

    def redo(self) -> None:
        self._editor.set_chunk(self._chunk_id, self._x, self._y, self._z)

    def undo(self) -> None:
        self._editor.set_chunk(self._previous_chunk, self._x, self._y, self._z)
