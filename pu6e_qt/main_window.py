from __future__ import annotations

from typing import Final

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QSizePolicy

import mapedit_gl as render
from U6 import Config, Map, obj
from pu6e_qt.actions import WorkbenchActions
from pu6e_qt.canvas import MapCanvas
from pu6e_qt.controller import EditorController
from pu6e_qt.docks import EditorDocks, create_docks
from pu6e_qt.renderer_settings import RendererRuntime


GAME_NAMES: Final[dict[str, str]] = {
    "fp": "Ultima VI: The False Prophet",
    "md": "Worlds of Ultima: Martian Dreams",
    "se": "Worlds of Ultima: The Savage Empire",
}


class MainWindow(QMainWindow):
    def __init__(self, controller: EditorController, renderer_runtime: RendererRuntime) -> None:
        super().__init__()
        self.controller = controller
        self.setObjectName("pu6e-workbench")
        self.setWindowTitle(
            f"pu6e Reloaded — Ultima world editor [Renderer: {renderer_runtime.display_name}]"
        )
        self.setMinimumSize(800, 560)
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )

        self.canvas = MapCanvas(controller)
        self.canvas.setObjectName("world-map")
        self.canvas.setAccessibleName("Ultima world map")
        self.setCentralWidget(self.canvas)

        self.docks: EditorDocks = create_docks(self, controller)
        self.actions = WorkbenchActions(self)
        self._create_status_bar()
        self._connect_editor_state()
        self._update_position(*controller.position)
        self.canvas.setFocus(Qt.FocusReason.OtherFocusReason)

    def _create_status_bar(self) -> None:
        status = self.statusBar()
        status.setSizeGripEnabled(False)

        self.game_label = QLabel(GAME_NAMES.get(str(Config.gametype), "Ultima world"))
        self.game_label.setObjectName("game-status")
        self.game_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        status.addWidget(self.game_label, 1)

        self.tool_label = QLabel("Inspect")
        self.tool_label.setObjectName("tool-status")
        status.addPermanentWidget(self.tool_label)

        self.location_label = QLabel()
        self.location_label.setObjectName("location-status")
        self.location_label.setAccessibleName("Current hexadecimal world coordinates")
        status.addPermanentWidget(self.location_label)

        self.zoom_label = QLabel()
        self.zoom_label.setObjectName("zoom-status")
        status.addPermanentWidget(self.zoom_label)

    def _connect_editor_state(self) -> None:
        self.controller.position_changed.connect(self._update_position)
        self.controller.location_selected.connect(self._select_location)
        self.controller.selected_object_changed.connect(self.docks.inspector.set_object)
        self.controller.changed.connect(self._mark_changed)
        self.controller.saved.connect(self._mark_saved)
        self.controller.terrain_mode_changed.connect(self.update_tool_status)
        self.canvas.fatal_error.connect(self._show_render_error)
        self.canvas.zoom_changed.connect(self._update_zoom)

    def _update_position(self, x: int, y: int, z: int) -> None:
        self.location_label.setText(f"X {x:03x}    Y {y:03x}    Z {z}")
        scale = render.scale_factor if hasattr(render, "scale_factor") else 1.0
        self._update_zoom(scale)

    def _update_zoom(self, scale: float) -> None:
        self.zoom_label.setText(f"{scale * 100:g}%")

    def _select_location(self, x: int, y: int, z: int) -> None:
        point = obj.objects_at(x, y, z)
        self.docks.stack.set_point(point, x, y, z)
        self.docks.chunks.set_mapchunk(x, y, z)
        self.docks.tiles.select_tile(Map.maptile_at(x, y, z))
        self.statusBar().showMessage(f"Selected {x:03x}, {y:03x}, level {z}", 3000)

    def _mark_changed(self, dirty: bool) -> None:
        self.setWindowModified(dirty)
        if dirty:
            self.statusBar().showMessage("Unsaved world changes", 3000)

    def _mark_saved(self) -> None:
        self.setWindowModified(False)
        self.statusBar().showMessage("World changes saved", 5000)

    def _show_render_error(self, message: str) -> None:
        QMessageBox.critical(self, "Unsupported OpenGL renderer", message)
        self.statusBar().showMessage(f"OpenGL unavailable: {message}")

    def update_tool_status(self, editing_terrain: bool) -> None:
        self.tool_label.setText("Terrain editing" if editing_terrain else "Inspect")
