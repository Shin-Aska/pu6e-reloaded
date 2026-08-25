from __future__ import annotations

from typing import Final, Protocol

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QSurfaceFormat, QWheelEvent
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication, QWidget

import mapedit_gl as render
from pu6e_qt.controller import EditorController
from pu6e_qt.map_input import MapInteraction
from pu6e_qt.map_navigation import navigation_action
from pu6e_qt.map_pan import PanAnchor, dragged_world_position

_ANIMATION_INTERVAL_MS: Final = 51


class OpenGLCompatibilityError(RuntimeError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(
            f"Ultima VI map rendering requires desktop compatibility-profile OpenGL: {reason}"
        )


class OpenGLContext(Protocol):
    def isOpenGLES(self) -> bool: ...

    def format(self) -> QSurfaceFormat: ...


def validate_opengl_context(context: OpenGLContext | None) -> None:
    if context is None:
        raise OpenGLCompatibilityError("Qt did not create an OpenGL context")
    if context.isOpenGLES():
        raise OpenGLCompatibilityError("OpenGL ES does not provide fixed-function APIs")
    if context.format().profile() == QSurfaceFormat.OpenGLContextProfile.CoreProfile:
        raise OpenGLCompatibilityError("a core-profile context removes fixed-function APIs")


def configure_opengl_format() -> QSurfaceFormat:
    surface_format = QSurfaceFormat()
    surface_format.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    surface_format.setVersion(2, 1)
    surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    surface_format.setOption(QSurfaceFormat.FormatOption.DeprecatedFunctions)
    surface_format.setDepthBufferSize(24)
    surface_format.setStencilBufferSize(8)
    surface_format.setSwapBehavior(QSurfaceFormat.SwapBehavior.DoubleBuffer)
    QSurfaceFormat.setDefaultFormat(surface_format)
    return surface_format


class MapCanvas(QOpenGLWidget):
    fatal_error = Signal(str)

    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.interaction = MapInteraction(controller)
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

    def initializeGL(self) -> None:
        try:
            validate_opengl_context(self.context())
        except OpenGLCompatibilityError as error:
            self.timer.stop()
            self.setEnabled(False)
            self.fatal_error.emit(str(error))
            return

        width, height = self._framebuffer_size(self.width(), self.height())
        render.InitGL(width, height)
        self._renderer_ready = True

    def resizeGL(self, width: int, height: int) -> None:
        if not self._renderer_ready:
            return
        framebuffer_width, framebuffer_height = self._framebuffer_size(width, height)
        render.Resize(framebuffer_width, framebuffer_height)

    def paintGL(self) -> None:
        if self._renderer_ready:
            render.draw()

    def _framebuffer_size(self, width: int, height: int) -> tuple[int, int]:
        ratio = self.devicePixelRatioF()
        return max(1, round(width * ratio)), max(1, round(height * ratio))

    def _world_at(self, position: QPointF) -> tuple[int, int, int]:
        ratio = self.devicePixelRatioF()
        return render.screen_to_world(position.x() * ratio, position.y() * ratio)

    def _advance_animation(self) -> None:
        render.tick()
        self.update()

    def zoom(self, factor: float) -> None:
        if factor <= 0:
            return
        render.scale_factor *= factor
        if self.isValid():
            self.makeCurrent()
            render.Resize(*self._framebuffer_size(self.width(), self.height()))
            self.doneCurrent()
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
        pixels_per_tile = 16.0 * render.scale_factor / self.devicePixelRatioF()
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
