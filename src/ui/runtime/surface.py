"""OpenGL surface requirements shared by editor startup and renderer probes."""

from __future__ import annotations

from typing import Protocol

from PySide6.QtGui import QSurfaceFormat


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
