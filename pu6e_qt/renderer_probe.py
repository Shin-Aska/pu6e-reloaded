from __future__ import annotations

from OpenGL import GL
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QApplication

from pu6e_qt.canvas import configure_opengl_format


def main() -> int:
    configure_opengl_format()
    application = QApplication([])
    widget = QOpenGLWidget()
    widget.resize(32, 32)
    widget.show()
    application.processEvents()
    if not widget.isValid():
        return 1
    widget.makeCurrent()
    renderer = GL.glGetString(GL.GL_RENDERER)
    return 0 if renderer is not None and b"zink" in renderer.lower() else 1


if __name__ == "__main__":
    raise SystemExit(main())
