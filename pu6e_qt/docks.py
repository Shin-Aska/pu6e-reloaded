from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow, QWidget

from pu6e_qt.controller import EditorController
from pu6e_qt.inspectors import ObjectInspector, ObjectStack
from pu6e_qt.minimap import WorldMinimap
from pu6e_qt.tiles import TileBrowser
from pu6e_qt.tools import BookViewer, ChunkInspector


@dataclass(frozen=True, slots=True)
class EditorDocks:
    stack: ObjectStack
    inspector: ObjectInspector
    tiles: TileBrowser
    chunks: ChunkInspector
    books: BookViewer
    minimap: WorldMinimap
    stack_dock: QDockWidget
    inspector_dock: QDockWidget
    tile_dock: QDockWidget
    chunk_dock: QDockWidget
    book_dock: QDockWidget
    minimap_dock: QDockWidget


def _dock(window: QMainWindow, title: str, widget: QWidget) -> QDockWidget:
    dock = QDockWidget(title, window)
    dock.setObjectName(title.casefold().replace(" ", "-"))
    dock.setWidget(widget)
    dock.setAllowedAreas(
        Qt.DockWidgetArea.LeftDockWidgetArea
        | Qt.DockWidgetArea.RightDockWidgetArea
        | Qt.DockWidgetArea.BottomDockWidgetArea
    )
    return dock


def create_docks(window: QMainWindow, controller: EditorController) -> EditorDocks:
    stack = ObjectStack(controller)
    inspector = ObjectInspector(controller)
    tiles = TileBrowser(controller)
    chunks = ChunkInspector(controller)
    books = BookViewer()
    minimap = WorldMinimap(controller)

    stack_dock = _dock(window, "Object stack", stack)
    inspector_dock = _dock(window, "Object properties", inspector)
    tile_dock = _dock(window, "Tile library", tiles)
    chunk_dock = _dock(window, "Map chunk", chunks)
    book_dock = _dock(window, "Books", books)
    minimap_dock = _dock(window, "World map", minimap)

    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, stack_dock)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, minimap_dock)
    window.splitDockWidget(stack_dock, minimap_dock, Qt.Orientation.Vertical)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, inspector_dock)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, tile_dock)
    window.splitDockWidget(inspector_dock, tile_dock, Qt.Orientation.Vertical)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, chunk_dock)
    window.tabifyDockWidget(tile_dock, chunk_dock)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, book_dock)
    window.tabifyDockWidget(tile_dock, book_dock)
    tile_dock.raise_()
    window.resizeDocks([stack_dock, inspector_dock], [260, 300], Qt.Orientation.Horizontal)
    window.resizeDocks([stack_dock, minimap_dock], [430, 270], Qt.Orientation.Vertical)

    return EditorDocks(
        stack,
        inspector,
        tiles,
        chunks,
        books,
        minimap,
        stack_dock,
        inspector_dock,
        tile_dock,
        chunk_dock,
        book_dock,
        minimap_dock,
    )
