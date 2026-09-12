from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QWidget,
)

from ui.app.controller import EditorController
from ui.shared.widgets import HexSpinBox


class ChunkInspector(QWidget):
    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._coordinates: tuple[int, int, int] | None = None
        self.chunk = HexSpinBox(0x3FF, self)
        self.chunk.setAccessibleName("Chunk identifier in hexadecimal")
        self.origin = QLabel("No world location selected", self)
        self.chunk_range = QLabel("0..3ff", self)
        layout = QFormLayout(self)
        layout.addRow("&Chunk", self.chunk)
        layout.addRow("Valid range", self.chunk_range)
        layout.addRow("Chunk origin", self.origin)
        self.chunk.valueChanged.connect(self._set_chunk)
        controller.position_changed.connect(self.set_mapchunk)
        controller.location_selected.connect(self.set_mapchunk)
        controller.session_changed.connect(self._session_changed)

    def _session_changed(self) -> None:
        self._coordinates = None
        self.origin.setText("No world location selected")
        blocker = QSignalBlocker(self.chunk)
        self.chunk.setValue(0)
        del blocker

    def set_mapchunk(self, x: int, y: int, z: int) -> None:
        if not self._controller.is_loaded:
            return
        chunk_id, tile_x, tile_y = self._controller.session.editor.chunk_at(x, y, z)
        self._coordinates = x, y, z
        blocker = QSignalBlocker(self.chunk)
        self.chunk.setValue(chunk_id)
        del blocker
        self.origin.setText(f"({x - tile_x:03x}, {y - tile_y:03x}, {z:x})")

    def _set_chunk(self, chunk_id: int) -> None:
        if self._coordinates is not None:
            x, y, z = self._coordinates
            self._controller.set_chunk(chunk_id, x, y, z)
