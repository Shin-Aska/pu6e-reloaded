from __future__ import annotations

import os
import ctypes
from collections.abc import MutableMapping
import sys

from pu6e_qt.vulkan_devices import (
    VulkanDeviceKind, list_vulkan_devices, parse_vulkan_device_selector,
)
from pu6e_qt.windows_vulkan import mesa_directory, vulkan_driver_manifest


def configure_windows_mesa(environment: MutableMapping[str, str]) -> None:
    if sys.platform != "win32":
        return
    if environment.get("PYOPENGL_PLATFORM") == "pu6e_mesa":
        environment.pop("PYOPENGL_PLATFORM")
        environment.pop("VK_DRIVER_FILES", None)
    if environment.get("GALLIUM_DRIVER") != "zink":
        return
    root = mesa_directory()
    library = root / "zink" / "opengl32.dll"
    if not library.is_file():
        return
    environment["QT_OPENGL"] = "software"
    environment["QT_OPENGL_DLL"] = str(library)
    environment["PYOPENGL_PLATFORM"] = "pu6e_mesa"
    if environment.get("LIBGL_ALWAYS_SOFTWARE") == "1":
        environment["VK_DRIVER_FILES"] = str(root / "lavapipe" / "lvp_icd.x86_64.json")
    else:
        selection = parse_vulkan_device_selector(
            environment.get("MESA_VK_DEVICE_SELECT", "auto").rstrip("!")
        )
        if selection is None:
            devices = list_vulkan_devices()
            device = next(
                (device for device in devices if device.kind is VulkanDeviceKind.DISCRETE),
                next(iter(devices), None),
            )
            selection = device.selector if device is not None else None
        manifest = vulkan_driver_manifest(selection)
        if manifest is not None:
            environment["VK_DRIVER_FILES"] = str(manifest)


def register_opengl_platform() -> None:
    if sys.platform == "win32" and os.environ.get("PYOPENGL_PLATFORM") == "pu6e_mesa":
        from OpenGL.plugins import PlatformPlugin

        loader = mesa_directory() / "vulkan-1.dll"
        if loader.is_file():
            ctypes.WinDLL(str(loader))
        PlatformPlugin("pu6e_mesa", "pu6e_qt.windows_opengl.MesaPlatform")
