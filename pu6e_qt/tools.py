from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QFormLayout, QLabel, QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget

from U6 import Map, book
from pu6e_qt.controller import EditorController
from pu6e_qt.widgets import HexSpinBox


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

    def set_mapchunk(self, x: int, y: int, z: int) -> None:
        chunk_id, tile_x, tile_y = Map.world_to_chunk_num(x, y, z)
        self._coordinates = x, y, z
        blocker = QSignalBlocker(self.chunk)
        self.chunk.setValue(chunk_id)
        del blocker
        self.origin.setText(f"({x - tile_x:03x}, {y - tile_y:03x}, {z:x})")

    def _set_chunk(self, chunk_id: int) -> None:
        if self._coordinates is not None:
            x, y, z = self._coordinates
            self._controller.set_chunk(chunk_id, x, y, z)


class BookViewer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.book_index = QSpinBox(self)
        self.book_index.setAccessibleName("Book index")
        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setAccessibleName("Book contents")
        layout = QVBoxLayout(self)
        layout.addWidget(self.book_index)
        layout.addWidget(self.text)
        self.book_index.valueChanged.connect(self._show_book)
        self.refresh()

    def refresh(self) -> None:
        if any(book.books):
            self.book_index.setRange(0, len(book.books) - 1)
            self.book_index.setEnabled(True)
            self._show_book(self.book_index.value())
            return
        self.book_index.setRange(0, 0)
        self.book_index.setEnabled(False)
        self.text.setPlainText("No book text is available for this game.")

    def set_book(self, index: int) -> None:
        if self.book_index.isEnabled():
            self.book_index.setValue(index)

    def _show_book(self, index: int) -> None:
        if self.book_index.isEnabled():
            self.text.setPlainText(book.contents(index))
