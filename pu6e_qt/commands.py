from __future__ import annotations

from PySide6.QtGui import QUndoCommand

from U6 import Map

class TilePaintCommand(QUndoCommand):
    def __init__(
        self,
        tile_id: int,
        x: int,
        y: int,
        z: int,
    ) -> None:
        super().__init__("Paint terrain")
        self._tile_id = tile_id
        self._x = x
        self._y = y
        self._z = z
        self._previous_tile = Map.maptile_at(x, y, z)

    def redo(self) -> None:
        Map.set_maptile_at(self._tile_id, self._x, self._y, self._z)

    def undo(self) -> None:
        Map.set_maptile_at(self._previous_tile, self._x, self._y, self._z)


class ChunkSetCommand(QUndoCommand):
    def __init__(
        self,
        chunk_id: int,
        x: int,
        y: int,
        z: int,
    ) -> None:
        super().__init__("Set map chunk")
        self._chunk_id = chunk_id
        self._x = x
        self._y = y
        self._z = z
        self._previous_chunk = Map.world_to_chunk_num(x, y, z)[0]

    def redo(self) -> None:
        Map.set_chunk_at(self._chunk_id, self._x, self._y, self._z)

    def undo(self) -> None:
        Map.set_chunk_at(self._previous_chunk, self._x, self._y, self._z)
