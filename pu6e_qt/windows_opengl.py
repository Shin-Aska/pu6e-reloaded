from __future__ import annotations

import ctypes
import os

from OpenGL.platform import baseplatform
from OpenGL.platform.win32 import Win32Platform


class MesaPlatform(Win32Platform):
    @baseplatform.lazy_property
    def GL(self) -> ctypes.WinDLL:
        return ctypes.WinDLL(os.environ["QT_OPENGL_DLL"])
