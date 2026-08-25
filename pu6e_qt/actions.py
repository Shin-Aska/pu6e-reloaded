from __future__ import annotations

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QSignalBlocker, QSize, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QComboBox, QDialog, QMessageBox, QToolBar

import mapedit_gl as render
from pu6e_qt.dialogs import GoToDialog
from pu6e_qt.icons import action_icon

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
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
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
        save.setIcon(action_icon("save"))
        save.setToolTip("Save changed objects, NPCs, and map data (Ctrl+S)")
        save.triggered.connect(self._save)
        self.file_menu.addAction(save)
        self.toolbar.addAction(save)

        quit_action = QAction("Quit", self.window)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.window.close)
        self.file_menu.addSeparator()
        self.file_menu.addAction(quit_action)

    def _install_edit_actions(self) -> None:
        undo = self.window.controller.undo_stack.createUndoAction(self.window, "Undo")
        undo.setShortcut(QKeySequence.StandardKey.Undo)
        undo.setIcon(action_icon("undo"))
        undo.setToolTip("Undo the latest world edit (Ctrl+Z)")
        redo = self.window.controller.undo_stack.createRedoAction(self.window, "Redo")
        redo.setShortcut(QKeySequence.StandardKey.Redo)
        redo.setIcon(action_icon("redo"))
        redo.setToolTip("Redo the latest world edit (Ctrl+Y)")
        self.edit_menu.addAction(undo)
        self.edit_menu.addAction(redo)
        self.toolbar.addAction(undo)
        self.toolbar.addAction(redo)
        self.toolbar.addSeparator()

    def _install_navigation_actions(self) -> None:
        goto = QAction("Go to coordinates…", self.window)
        goto.setIcon(action_icon("locate"))
        goto.setShortcut(QKeySequence("Ctrl+G"))
        goto.setToolTip("Jump to hexadecimal world coordinates (Ctrl+G)")
        goto.triggered.connect(self._show_goto)
        self.tools_menu.addAction(goto)
        self.toolbar.addAction(goto)
        self.toolbar.addSeparator()

        self.zoom_in = QAction(action_icon("zoom-in"), "Zoom in", self.window)
        self.zoom_in.setShortcuts([QKeySequence("+"), QKeySequence("=")])
        self.zoom_in.setToolTip("Zoom in (+)")
        self.zoom_in.triggered.connect(lambda: self.window.canvas.zoom(2.0))
        self.zoom_out = QAction(action_icon("zoom-out"), "Zoom out", self.window)
        self.zoom_out.setShortcut(QKeySequence("-"))
        self.zoom_out.setToolTip("Zoom out (-)")
        self.zoom_out.triggered.connect(lambda: self.window.canvas.zoom(0.5))
        self.view_menu.addAction(self.zoom_in)
        self.view_menu.addAction(self.zoom_out)
        self.toolbar.addAction(self.zoom_out)

        self.zoom_selector = QComboBox(self.toolbar)
        self.zoom_selector.setObjectName("zoom-selector")
        self.zoom_selector.setAccessibleName("World map zoom percentage")
        self.zoom_selector.setToolTip("Choose the world map zoom percentage")
        self.zoom_selector.addItems(("12.5%", "25%", "50%", "100%", "200%", "400%"))
        self.zoom_selector.setMinimumWidth(84)
        self._sync_zoom(render.scale_factor)
        self.zoom_selector.currentTextChanged.connect(self._apply_zoom)
        self.window.canvas.zoom_changed.connect(self._sync_zoom)
        self.toolbar.addWidget(self.zoom_selector)
        self.toolbar.addAction(self.zoom_in)

        actual_size = QAction(action_icon("actual-size"), "Actual size", self.window)
        actual_size.setShortcut(QKeySequence("Ctrl+0"))
        actual_size.setToolTip("Reset the world map to 100% (Ctrl+0)")
        actual_size.triggered.connect(lambda: self._apply_zoom("100%"))
        self.view_menu.addAction(actual_size)
        self.toolbar.addAction(actual_size)
        self.toolbar.addSeparator()

        surface = QAction(action_icon("layers"), "Return to surface", self.window)
        surface.setToolTip("Return directly to the surface world")
        surface.triggered.connect(lambda: self.window.controller.change_level(0))
        self.tools_menu.addAction(surface)
        self.toolbar.addAction(surface)

        self.level_selector = QComboBox(self.toolbar)
        self.level_selector.setObjectName("world-level-selector")
        self.level_selector.setAccessibleName("World level")
        self.level_selector.setToolTip("Jump directly to the surface or an underworld level")
        self.level_selector.addItem("Surface")
        for level in range(1, 6):
            self.level_selector.addItem(f"Underworld {level}")
        self.level_selector.setCurrentIndex(self.window.controller.position[2])
        self.level_selector.currentIndexChanged.connect(self.window.controller.change_level)
        self.window.controller.position_changed.connect(self._sync_level)
        self.toolbar.addWidget(self.level_selector)

        ascend = QAction(action_icon("ascend"), "Ascend one level", self.window)
        ascend.setShortcut(QKeySequence("Alt+Up"))
        ascend.setToolTip("Ascend one world level (Alt+Up)")
        ascend.triggered.connect(lambda: self._change_level(-1))
        descend = QAction(action_icon("descend"), "Descend one level", self.window)
        descend.setShortcut(QKeySequence("Alt+Down"))
        descend.setToolTip("Descend one world level (Alt+Down)")
        descend.triggered.connect(lambda: self._change_level(1))
        self.tools_menu.addAction(ascend)
        self.tools_menu.addAction(descend)
        self.toolbar.addAction(ascend)
        self.toolbar.addAction(descend)
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
                action.setIcon(action_icon("grid" if attribute == "display_grid" else "objects"))
                action.setToolTip(f"Toggle {label.lower()} ({shortcut})")
                self.toolbar.addAction(action)

        self.terrain = QAction(action_icon("terrain"), "Edit terrain", self.window)
        self.terrain.setObjectName("toggle-terrain")
        self.terrain.setCheckable(True)
        self.terrain.setShortcut(QKeySequence("Ctrl+T"))
        self.terrain.setToolTip("Toggle terrain editing (Ctrl+T)")
        self.terrain.toggled.connect(self._toggle_terrain)
        self.tools_menu.addAction(self.terrain)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.terrain)

        quests = QAction(action_icon("quests"), "Quests and NPCs", self.window)
        quests.setShortcut(QKeySequence("Ctrl+K"))
        quests.setToolTip("Browse character dialogue and quest clues (Ctrl+K)")
        quests.triggered.connect(self._show_quests)
        self.tools_menu.addAction(quests)
        self.toolbar.addAction(quests)

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
            (docks.minimap_dock, "M"),
            (docks.quest_dock, ""),
        ):
            action = dock.toggleViewAction()
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            self.window_menu.addAction(action)

    def _sync_zoom(self, scale: float) -> None:
        label = f"{scale * 100:g}%"
        blocker = QSignalBlocker(self.zoom_selector)
        if self.zoom_selector.findText(label) < 0:
            self.zoom_selector.addItem(label)
        self.zoom_selector.setCurrentText(label)
        del blocker

    def _apply_zoom(self, label: str) -> None:
        target = float(label.removesuffix("%")) / 100.0
        self.window.canvas.zoom(target / render.scale_factor)

    def _sync_level(self, x: int, y: int, z: int) -> None:
        blocker = QSignalBlocker(self.level_selector)
        self.level_selector.setCurrentIndex(z)
        del blocker

    def _change_level(self, delta: int) -> None:
        current = self.window.controller.position[2]
        self.window.controller.change_level(max(0, min(5, current + delta)))

    def _show_quests(self) -> None:
        self.window.docks.quest_dock.show()
        self.window.docks.quest_dock.raise_()
        self.window.docks.quests.search.setFocus()

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
