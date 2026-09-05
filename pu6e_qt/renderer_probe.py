from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main(report_path: Path | None = None) -> int:
    from pu6e_qt.renderer_settings import RendererMode, configure_renderer
    from pu6e_qt.vulkan_devices import parse_vulkan_device_selector

    configure_renderer(
        RendererMode.VULKAN,
        os.environ.get("LIBGL_ALWAYS_SOFTWARE") == "1",
        parse_vulkan_device_selector(os.environ.get("MESA_VK_DEVICE_SELECT", "auto").rstrip("!")),
    )
    from OpenGL import GL
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import QApplication
    from pu6e_qt.canvas import configure_opengl_format

    configure_opengl_format()
    application = QApplication([])
    widget = QOpenGLWidget()
    widget.resize(32, 32)
    widget.show()
    application.processEvents()
    renderer = None
    pixel = b""
    if widget.isValid():
        widget.makeCurrent()
        renderer = GL.glGetString(GL.GL_RENDERER)
        GL.glViewport(0, 0, 32, 32)
        GL.glClearColor(0, 0, 0, 1)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glBegin(GL.GL_TRIANGLES)
        GL.glColor3f(1, 0, 0)
        GL.glVertex2f(-1, -1)
        GL.glVertex2f(1, -1)
        GL.glVertex2f(0, 1)
        GL.glEnd()
        pixel = bytes(GL.glReadPixels(16, 16, 1, 1, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE))
        widget.doneCurrent()
    widget.close()
    if report_path is not None:
        report_path.write_text(json.dumps({
            "renderer": renderer.decode("utf-8", errors="replace") if renderer else None,
            "pixel": pixel.hex(),
        }), encoding="utf-8")
    return 0 if renderer and b"zink" in renderer.lower() and pixel == b"\xff\0\0\xff" else 1


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]) if len(sys.argv) == 2 else None))
