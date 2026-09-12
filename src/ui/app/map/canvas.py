from __future__ import annotations

from typing import Final

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QWidget

from ui.app.controller import EditorController
from ui.app.map.interaction import MapInteraction
from ui.app.map.navigation import navigation_action
from ui.app.map.pan import PanAnchor, dragged_world_position
from ui.rendering.renderer import MapRenderer
from ui.runtime.surface import OpenGLCompatibilityError, validate_opengl_context

_ANIMATION_INTERVAL_MS: Final = 51
MINIMUM_ZOOM: Final = 0.25
MAXIMUM_ZOOM: Final = 4.0


class MapCanvas(QOpenGLWidget):
    fatal_error = Signal(str)
    zoom_changed = Signal(float)

    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.interaction = MapInteraction(controller)
        self.renderer = MapRenderer(controller.session, controller.camera, controller.render_options)
        self._pan_anchor: PanAnchor | None = None
        self._pending_pan: QPointF | None = None
        self._pan_button = Qt.MouseButton.NoButton
        self._renderer_ready = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self.timer = QTimer(self)
        self.timer.setInterval(_ANIMATION_INTERVAL_MS)
        self.timer.timeout.connect(self._advance_animation)
        self.timer.start()
        self.controller.position_changed.connect(self.update)
        self.controller.changed.connect(self.update)
        self.controller.session_changed.connect(self._replace_session)

    def initializeGL(self) -> None:
        try:
            validate_opengl_context(self.context())
        except OpenGLCompatibilityError as error:
            self.timer.stop()
            self.setEnabled(False)
            self.fatal_error.emit(str(error))
            return

        width, height = self._framebuffer_size(self.width(), self.height())
        self.renderer.initialize(width, height)
        self._renderer_ready = True
        context = self.context()
        if context is not None:
            context.aboutToBeDestroyed.connect(self._dispose_renderer)

    def _dispose_renderer(self) -> None:
        self.makeCurrent()
        try:
            self.renderer.dispose()
        finally:
            self.doneCurrent()
            self._renderer_ready = False

    def _replace_session(self) -> None:
        self._end_pan()
        if self._renderer_ready:
            self.makeCurrent()
        try:
            self.renderer.set_session(self.controller.session)
        finally:
            if self._renderer_ready:
                self.doneCurrent()
        self.update()

    def resizeGL(self, width: int, height: int) -> None:
        if not self._renderer_ready:
            return
        framebuffer_width, framebuffer_height = self._framebuffer_size(width, height)
        self.renderer.resize(framebuffer_width, framebuffer_height)

    def paintGL(self) -> None:
        if self._renderer_ready:
            self.renderer.paint()

    def _framebuffer_size(self, width: int, height: int) -> tuple[int, int]:
        ratio = self.devicePixelRatioF()
        return max(1, round(width * ratio)), max(1, round(height * ratio))

    def _world_at(self, position: QPointF) -> tuple[int, int, int]:
        ratio = self.devicePixelRatioF()
        return self.controller.camera.screen_to_world(position.x() * ratio, position.y() * ratio)

    def _advance_animation(self) -> None:
        self.renderer.tick()
        self.update()

    def zoom(self, factor: float) -> None:
        if factor <= 0:
            return
        camera = self.controller.camera
        scale = max(MINIMUM_ZOOM, min(MAXIMUM_ZOOM, camera.scale * factor))
        if scale == camera.scale:
            return
        camera.set_zoom(scale)
        camera.resize(*self._framebuffer_size(self.width(), self.height()))
        if self._renderer_ready and self.isValid():
            self.makeCurrent()
            try:
                self.renderer.resize(camera.width, camera.height)
            finally:
                self.doneCurrent()
        self.zoom_changed.emit(camera.scale)
        self.update()

    def set_coords(self, x: int, y: int, z: int) -> None:
        self.controller.set_position(x, y, z)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        modifiers = event.modifiers()
        prohibited = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
        if modifiers & prohibited:
            super().keyPressEvent(event)
            return

        keypad = bool(modifiers & Qt.KeyboardModifier.KeypadModifier)
        action = navigation_action(event.key(), keypad=keypad)
        if action is None:
            super().keyPressEvent(event)
            return

        if action.zoom_factor != 1.0:
            self.zoom(action.zoom_factor)
        elif action.level_delta:
            self.controller.change_level(self.controller.position[2] + action.level_delta)
        else:
            x, y, z = self.controller.position
            self.controller.set_position(x + action.dx, y + action.dy, z)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._begin_pan(event.position(), event.button())
            event.accept()
            return

        x, y, z = self._world_at(event.position())
        if event.button() == Qt.MouseButton.LeftButton:
            self.interaction.press_left(x, y, z)
            origin = self.interaction.drag_origin
            if (
                origin is not None
                and origin.item is None
                and not self.controller.terrain_mode
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
            ):
                self._pending_pan = event.position()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.interaction.press_right(x, y, z)
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == self._pan_button:
            self._end_pan()
            self.interaction.drag_origin = None
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self._pending_pan = None
            x, y, z = self._world_at(event.position())
            modifiers = event.modifiers()
            self.interaction.release_left(
                x,
                y,
                z,
                shift=bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
                control=bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            )
            self.update()
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton:
            self.interaction.release_right()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._pan_anchor is not None:
            self._continue_pan(event.position())
            event.accept()
            return
        if self._pending_pan is not None and event.buttons() & Qt.MouseButton.LeftButton:
            distance = (event.position() - self._pending_pan).manhattanLength()
            if distance >= QApplication.startDragDistance():
                self._begin_pan(self._pending_pan, Qt.MouseButton.LeftButton)
                self._continue_pan(event.position())
            event.accept()
            return
        if event.buttons() & Qt.MouseButton.RightButton:
            if self.interaction.drag_right(*self._world_at(event.position())):
                self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def _begin_pan(self, pointer: QPointF, button: Qt.MouseButton) -> None:
        self._pan_anchor = PanAnchor(pointer, self.controller.position)
        self._pan_button = button
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _continue_pan(self, pointer: QPointF) -> None:
        anchor = self._pan_anchor
        if anchor is None:
            return
        pixels_per_tile = 16.0 * self.controller.camera.scale / self.devicePixelRatioF()
        position = dragged_world_position(anchor, pointer, pixels_per_tile)
        if position != self.controller.position:
            self.controller.set_position(*position)

    def _end_pan(self) -> None:
        self._pan_anchor = None
        self._pending_pan = None
        self._pan_button = Qt.MouseButton.NoButton
        self.unsetCursor()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta:
            self.zoom(2.0 if delta > 0 else 0.5)
            event.accept()
            return
        super().wheelEvent(event)
