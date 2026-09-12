from __future__ import annotations

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget

from ui.app.controller import EditorController


class BookViewer(QWidget):
    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._controller = controller
        self._books: tuple[str, ...] = ()
        self.book_index = QSpinBox(self)
        self.book_index.setAccessibleName("Book index")
        self.text = QPlainTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setAccessibleName("Book contents")
        layout = QVBoxLayout(self)
        layout.addWidget(self.book_index)
        layout.addWidget(self.text)
        self.book_index.valueChanged.connect(self._show_book)
        controller.session_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self._books = (
            self._controller.session.state.assets.books if self._controller.is_loaded else ()
        )
        blocker = QSignalBlocker(self.book_index)
        self.book_index.setValue(0)
        if any(self._books):
            self.book_index.setRange(0, len(self._books) - 1)
            self.book_index.setEnabled(True)
            self._show_book(0)
            del blocker
            return
        self.book_index.setRange(0, 0)
        self.book_index.setEnabled(False)
        self.text.setPlainText("No book text is available for this game.")
        del blocker

    def set_book(self, index: int) -> None:
        if self.book_index.isEnabled():
            self.book_index.setValue(index)

    def _show_book(self, index: int) -> None:
        if self.book_index.isEnabled():
            self.text.setPlainText(self._books[index])
