from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QDialog, QMessageBox, QToolBar

import mapedit_gl as render
from pu6e_qt.dialogs import GoToDialog

if TYPE_CHECKING:
    from pu6e_qt.main_window import MainWindow


OVERLAYS: Final[tuple[tuple[str, str, str], ...]] = (
    ("Grid", "display_grid", "G"),
    ("Objects", "display_objects", "O"),
    ("Animated tiles", "animate_tiles", "A"),
    ("Palette rotation", "rotate_palette", "P"),
    ("Hybrid tiles", "hybrid_tiles", "H"),
    ("Coordinates", "display_coords", "L"),
)


class WorkbenchActions:
    def __init__(self, window: MainWindow) -> None:
        self.window = window
        self.toolbar = QToolBar("Map tools", window)
        self.toolbar.setObjectName("map-tools")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        window.addToolBar(self.toolbar)

        self.file_menu = window.menuBar().addMenu("&File")
        self.edit_menu = window.menuBar().addMenu("&Edit")
        self.view_menu = window.menuBar().addMenu("&View")
        self.tools_menu = window.menuBar().addMenu("&Tools")
        self.window_menu = window.menuBar().addMenu("&Window")

        self._install_file_actions()
        self._install_edit_actions()
        self._install_navigation_actions()
        self._install_view_actions()
        self._install_dock_actions()

    def _install_file_actions(self) -> None:
        save = QAction("Save world", self.window)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.setToolTip("Save changed objects, NPCs, and map data (Ctrl+S)")
        save.triggered.connect(self._save)
        self.file_menu.addAction(save)
        self.toolbar.addAction(save)
        self.toolbar.addSeparator()

        quit_action = QAction("Quit", self.window)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.window.close)
        self.file_menu.addSeparator()
        self.file_menu.addAction(quit_action)

    def _install_edit_actions(self) -> None:
        undo = self.window.controller.undo_stack.createUndoAction(self.window, "Undo")
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        redo = self.window.controller.undo_stack.createRedoAction(self.window, "Redo")
        redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.edit_menu.addAction(undo)
        self.edit_menu.addAction(redo)

    def _install_navigation_actions(self) -> None:
        goto = QAction("Go to coordinates…", self.window)
        goto.setShortcut(QKeySequence("Ctrl+G"))
        goto.setToolTip("Jump to hexadecimal world coordinates (Ctrl+G)")
        goto.triggered.connect(self._show_goto)
        self.tools_menu.addAction(goto)
        self.toolbar.addAction(goto)

        zoom_in = QAction("Zoom in", self.window)
        zoom_in.setShortcuts([QKeySequence("+"), QKeySequence("=")])
        zoom_in.triggered.connect(lambda: self.window.canvas.zoom(2.0))
        zoom_out = QAction("Zoom out", self.window)
        zoom_out.setShortcut(QKeySequence("-"))
        zoom_out.triggered.connect(lambda: self.window.canvas.zoom(0.5))
        self.view_menu.addAction(zoom_in)
        self.view_menu.addAction(zoom_out)
        self.toolbar.addAction(zoom_out)
        self.toolbar.addAction(zoom_in)
        self.toolbar.addSeparator()

    def _install_view_actions(self) -> None:
        self.view_menu.addSeparator()
        for label, attribute, shortcut in OVERLAYS:
            action = QAction(label, self.window)
            action.setObjectName(f"toggle-{attribute}")
            action.setCheckable(True)
            action.setChecked(bool(getattr(render, attribute)))
            action.setShortcut(QKeySequence(shortcut))
            action.toggled.connect(
                lambda checked, name=attribute: self._toggle_overlay(name, checked)
            )
            self.view_menu.addAction(action)
            if attribute in {"display_grid", "display_objects"}:
                self.toolbar.addAction(action)

        self.terrain = QAction("Edit terrain", self.window)
        self.terrain.setObjectName("toggle-terrain")
        self.terrain.setCheckable(True)
        self.terrain.setShortcut(QKeySequence("Ctrl+T"))
        self.terrain.toggled.connect(self._toggle_terrain)
        self.tools_menu.addAction(self.terrain)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.terrain)

        fullscreen = QAction("Fullscreen", self.window)
        fullscreen.setCheckable(True)
        fullscreen.setShortcut(QKeySequence("F"))
        fullscreen.toggled.connect(self._toggle_fullscreen)
        self.view_menu.addSeparator()
        self.view_menu.addAction(fullscreen)

    def _install_dock_actions(self) -> None:
        docks = self.window.docks
        for dock, shortcut in (
            (docks.stack_dock, "S"),
            (docks.inspector_dock, ""),
            (docks.tile_dock, "T"),
            (docks.chunk_dock, "C"),
            (docks.book_dock, ""),
        ):
            action = dock.toggleViewAction()
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            self.window_menu.addAction(action)

    def _toggle_overlay(self, attribute: str, checked: bool) -> None:
        setattr(render, attribute, int(checked))
        if attribute == "display_objects" and not checked:
            render.fade_objects = 1.0
        self.window.canvas.update()

    def _toggle_terrain(self, enabled: bool) -> None:
        self.window.controller.set_terrain_mode(enabled)
        self.window.update_tool_status(enabled)

    def _toggle_fullscreen(self, enabled: bool) -> None:
        render.fullscreen = int(enabled)
        if enabled:
            self.window.showFullScreen()
        else:
            self.window.showNormal()

    def _show_goto(self) -> None:
        dialog = GoToDialog(self.window.controller.position, self.window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.window.controller.set_position(*dialog.values())
            self.window.canvas.setFocus()

    def _save(self) -> None:
        try:
            self.window.controller.save()
        except (OSError, ValueError) as error:
            QMessageBox.critical(self.window, "Unable to save world", str(error))
            self.window.statusBar().showMessage(f"Save failed: {error}", 8000)
