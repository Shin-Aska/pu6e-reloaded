# ruff: noqa: D102, N802, PLR0913, PLR0917
# Signatures and names match the external OpenGL API exactly.
"""Checked type boundary for dynamically generated compatibility OpenGL bindings."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Final, Literal, Protocol, SupportsInt, override, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np
    from numpy.typing import NDArray


@runtime_checkable
class CompatibilityGL(Protocol):
    """Typed boundary for the fixed-function calls provided by PyOpenGL's dynamic module."""

    GL_ALPHA_TEST: int
    GL_BLEND: int
    GL_COLOR_BUFFER_BIT: int
    GL_DEPTH_BUFFER_BIT: int
    GL_DEPTH_TEST: int
    GL_FLAT: int
    GL_FLOAT: int
    GL_GREATER: int
    GL_LEQUAL: int
    GL_LINEAR: int
    GL_MODELVIEW: int
    GL_MODULATE: int
    GL_NEAREST: int
    GL_ONE_MINUS_SRC_ALPHA: int
    GL_PROJECTION: int
    GL_QUADS: int
    GL_REPLACE: int
    GL_RGBA: int
    GL_SRC_ALPHA: int
    GL_TEXTURE_2D: int
    GL_TEXTURE_COORD_ARRAY: int
    GL_TEXTURE_ENV: int
    GL_TEXTURE_ENV_MODE: int
    GL_TEXTURE_MAG_FILTER: int
    GL_TEXTURE_MIN_FILTER: int
    GL_UNPACK_ALIGNMENT: int
    GL_UNSIGNED_BYTE: int
    GL_VERTEX_ARRAY: int

    def glAlphaFunc(self, function: int, reference: float) -> None: ...
    def glBegin(self, mode: int) -> None: ...
    def glBindTexture(self, target: int, texture: int) -> None: ...
    def glBlendFunc(self, source: int, destination: int) -> None: ...
    def glClear(self, mask: int) -> None: ...
    def glClearColor(self, red: float, green: float, blue: float, alpha: float) -> None: ...
    def glClearDepth(self, depth: float) -> None: ...
    def glColor4f(self, red: float, green: float, blue: float, alpha: float) -> None: ...
    def glDeleteTextures(self, textures: Sequence[int]) -> None: ...
    def glDepthFunc(self, function: int) -> None: ...
    def glDisable(self, capability: int) -> None: ...
    def glDisableClientState(self, capability: int) -> None: ...
    def glDrawArrays(self, mode: int, first: int, count: int) -> None: ...
    def glEnable(self, capability: int) -> None: ...
    def glEnableClientState(self, capability: int) -> None: ...
    def glEnd(self) -> None: ...
    def glGenTextures(self, count: Literal[1]) -> SupportsInt: ...
    def glLoadIdentity(self) -> None: ...
    def glMatrixMode(self, mode: int) -> None: ...
    def glOrtho(
        self, left: float, right: float, bottom: float, top: float, near: float, far: float
    ) -> None: ...
    def glPixelStorei(self, parameter: int, value: int) -> None: ...
    def glPopMatrix(self) -> None: ...
    def glPushMatrix(self) -> None: ...
    def glShadeModel(self, mode: int) -> None: ...
    def glTexCoord2f(self, s: float, t: float) -> None: ...
    def glTexCoordPointer(
        self, size: int, kind: int, stride: int, pointer: NDArray[np.float32]
    ) -> None: ...
    def glTexEnvf(self, target: int, parameter: int, value: float) -> None: ...
    def glTexImage2D(
        self,
        target: int,
        level: int,
        internal: int,
        width: int,
        height: int,
        border: int,
        pixel_format: int,
        kind: int,
        pixels: bytes,
    ) -> None: ...
    def glTexParameterf(self, target: int, parameter: int, value: float) -> None: ...
    def glTexSubImage2D(
        self,
        target: int,
        level: int,
        x: int,
        y: int,
        width: int,
        height: int,
        pixel_format: int,
        kind: int,
        pixels: bytes,
    ) -> None: ...
    def glVertex3f(self, x: float, y: float, z: float) -> None: ...
    def glVertexPointer(
        self, size: int, kind: int, stride: int, pointer: NDArray[np.float32]
    ) -> None: ...
    def glViewport(self, x: int, y: int, width: int, height: int) -> None: ...


class OpenGLBindingError(RuntimeError):
    """The imported bindings lack required fixed-function operations."""

    def __init__(self, module: str) -> None:
        self.module: str = module
        super().__init__(module)

    @override
    def __str__(self) -> str:
        return f"{self.module} does not provide the required compatibility OpenGL API"


def load_gl() -> CompatibilityGL:
    """Load and validate the installed compatibility OpenGL bindings."""
    bindings = import_module("OpenGL.GL")
    if not isinstance(bindings, CompatibilityGL):
        raise OpenGLBindingError(bindings.__name__)
    return bindings


GL: Final[CompatibilityGL] = load_gl()
