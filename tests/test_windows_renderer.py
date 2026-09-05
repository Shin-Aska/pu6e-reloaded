from __future__ import annotations

import os
import json
from pathlib import Path
import subprocess
import sys
from typing import Final

import pytest

_PROJECT: Final = Path(__file__).resolve().parents[1]


def test_application_import_keeps_opengl_unbound_until_renderer_selection() -> None:
    # Given: a fresh process where no graphics library has been selected.
    # When: the application entry module is imported.
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import pu6e_qt.application; "
         "raise SystemExit(int('OpenGL.GL' in sys.modules))"],
        cwd=_PROJECT, capture_output=True, text=True, timeout=20,
    )

    # Then: renderer selection can still bind PyOpenGL to the chosen library.
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="Windows graphics integration")
@pytest.mark.parametrize("software", (False, True))
def test_windows_vulkan_draws_with_the_bundled_runtime(software: bool) -> None:
    # Given: the Windows runtime prepared by the release build.
    runtime = _PROJECT / "build" / "mesa" / "runtime"
    if not (runtime / "zink" / "opengl32.dll").is_file():
        pytest.skip("Run packaging/prepare-windows-mesa.ps1 first")
    if not software:
        from pu6e_qt.vulkan_devices import VulkanDeviceKind, list_vulkan_devices

        if not any(device.kind is not VulkanDeviceKind.CPU for device in list_vulkan_devices()):
            pytest.skip("This host has no hardware Vulkan device")
    environment = os.environ.copy()
    environment.pop("QT_QPA_PLATFORM", None)

    # When: a fresh Qt process renders a fixed-function triangle through Vulkan.
    script = f"""
from pu6e_qt.renderer_settings import configure_renderer, RendererMode
configure_renderer(RendererMode.VULKAN, {software!r})
from OpenGL import GL
from PySide6.QtWidgets import QApplication
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from pu6e_qt.canvas import configure_opengl_format
configure_opengl_format()
app = QApplication([])
widget = QOpenGLWidget()
widget.resize(32, 32)
widget.show()
app.processEvents()
assert widget.isValid(), 'No OpenGL context'
widget.makeCurrent()
renderer = GL.glGetString(GL.GL_RENDERER)
print(renderer, flush=True)
assert renderer is not None and b'zink' in renderer.lower(), renderer
assert (b'llvmpipe' in renderer.lower()) == {software!r}, renderer
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
assert pixel == bytes((255, 0, 0, 255)), pixel
widget.doneCurrent()
widget.close()
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=_PROJECT, env=environment,
        capture_output=True, text=True, timeout=40,
    )

    # Then: Qt and PyOpenGL share a working hardware or CPU Zink context.
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(sys.platform != "win32", reason="Windows graphics integration")
def test_renderer_probe_reports_verified_pixels(tmp_path: Path) -> None:
    # Given: the same CPU Vulkan environment used by the packaged smoke check.
    from pu6e_qt.renderer_settings import RendererMode, _set_renderer_environment

    if not (_PROJECT / "build/mesa/runtime/zink/opengl32.dll").is_file():
        pytest.skip("Run packaging/prepare-windows-mesa.ps1 first")
    environment = os.environ.copy()
    _set_renderer_environment(RendererMode.VULKAN, environment, True, None)
    report = tmp_path / "probe.json"

    # When: the real probe writes its rendering result for release validation.
    result = subprocess.run(
        [sys.executable, "-m", "pu6e_qt.renderer_probe", str(report)],
        cwd=_PROJECT, env=environment, capture_output=True, text=True, timeout=40,
    )

    # Then: the release can verify pixels and the actual backend, beyond a window title.
    assert result.returncode == 0, result.stdout + result.stderr
    assert report.is_file()
    data = json.loads(report.read_text(encoding="utf-8"))
    assert "zink" in data["renderer"].lower()
    assert data["pixel"] == "ff0000ff"
