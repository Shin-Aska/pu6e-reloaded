from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Final, assert_never

from PySide6.QtCore import QCoreApplication, Qt

from pu6e_qt.renderer_preferences import (
    RENDERER_MODES,
    RendererMode,
    read_renderer_mode,
)
from pu6e_qt.vulkan_devices import (
    VulkanDeviceKind,
    VulkanDeviceSelector,
    list_vulkan_devices,
    read_vulkan_gpu,
)

_GRAPHICS_ENVIRONMENT: Final = (
    "QT_OPENGL",
    "LIBGL_ALWAYS_SOFTWARE",
    "GALLIUM_DRIVER",
    "MESA_LOADER_DRIVER_OVERRIDE",
    "LIBGL_KOPPER_DRI2",
    "QSG_RHI_BACKEND",
    "MESA_VK_DEVICE_SELECT",
)


@dataclass(frozen=True, slots=True)
class RendererRuntime:
    renderer: RendererMode
    software_vulkan: bool = False
    notice: str | None = None
    vulkan_gpu: VulkanDeviceSelector | None = None

    @property
    def display_name(self) -> str:
        return f"{self.renderer.label} (CPU)" if self.software_vulkan else self.renderer.label


def _set_renderer_environment(
    renderer: RendererMode,
    environment: MutableMapping[str, str],
    software_vulkan: bool,
    vulkan_gpu: VulkanDeviceSelector | None,
) -> None:
    for name in _GRAPHICS_ENVIRONMENT:
        environment.pop(name, None)

    match renderer:
        case RendererMode.SOFTWARE:
            environment.update(
                QT_OPENGL="software",
                LIBGL_ALWAYS_SOFTWARE="1",
                GALLIUM_DRIVER="llvmpipe",
            )
        case RendererMode.OPENGL:
            environment["QT_OPENGL"] = "desktop"
        case RendererMode.VULKAN:
            environment.update(
                QT_OPENGL="desktop",
                GALLIUM_DRIVER="zink",
                MESA_LOADER_DRIVER_OVERRIDE="zink",
                LIBGL_KOPPER_DRI2="1",
                QSG_RHI_BACKEND="vulkan",
            )
            if software_vulkan:
                environment["LIBGL_ALWAYS_SOFTWARE"] = "1"
            if vulkan_gpu is not None:
                environment["MESA_VK_DEVICE_SELECT"] = f"{vulkan_gpu}!"
        case unreachable:
            assert_never(unreachable)


def configure_renderer(
    renderer: RendererMode,
    software_vulkan: bool = False,
    vulkan_gpu: VulkanDeviceSelector | None = None,
) -> None:
    _set_renderer_environment(renderer, os.environ, software_vulkan, vulkan_gpu)

    match renderer:
        case RendererMode.SOFTWARE:
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseSoftwareOpenGL,
                True,
            )
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseDesktopOpenGL,
                False,
            )
        case RendererMode.OPENGL:
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseSoftwareOpenGL,
                False,
            )
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseDesktopOpenGL,
                True,
            )
        case RendererMode.VULKAN:
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseSoftwareOpenGL,
                False,
            )
            QCoreApplication.setAttribute(
                Qt.ApplicationAttribute.AA_UseDesktopOpenGL,
                True,
            )
        case unreachable:
            assert_never(unreachable)


def _probe_vulkan_environment(
    software_vulkan: bool,
    vulkan_gpu: VulkanDeviceSelector | None,
) -> bool:
    environment = os.environ.copy()
    _set_renderer_environment(
        RendererMode.VULKAN,
        environment,
        software_vulkan,
        vulkan_gpu,
    )
    command = (
        (sys.executable, "--renderer-probe")
        if getattr(sys, "frozen", False)
        else (sys.executable, "-m", "pu6e_qt.renderer_probe")
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def resolve_renderer(
    renderer: RendererMode,
    vulkan_gpu: VulkanDeviceSelector | None = None,
) -> RendererRuntime:
    match renderer:
        case RendererMode.SOFTWARE | RendererMode.OPENGL:
            return RendererRuntime(renderer)
        case RendererMode.VULKAN:
            devices = list_vulkan_devices()
            selected_gpu = vulkan_gpu
            selection_notice = None
            selected_device = next(
                (device for device in devices if device.selector == selected_gpu),
                None,
            )
            if (
                selected_gpu is not None
                and selected_device is None
            ):
                selected_gpu = None
                selection_notice = (
                    "The saved Vulkan GPU is no longer available, so pu6e Reloaded "
                    "is using Automatic GPU selection for this session."
                )
            if (
                selected_device is not None
                and selected_device.kind is VulkanDeviceKind.CPU
                and _probe_vulkan_environment(True, selected_gpu)
            ):
                return RendererRuntime(
                    RendererMode.VULKAN,
                    software_vulkan=True,
                    vulkan_gpu=selected_gpu,
                )
            if _probe_vulkan_environment(False, selected_gpu):
                return RendererRuntime(
                    RendererMode.VULKAN,
                    notice=selection_notice,
                    vulkan_gpu=selected_gpu,
                )
            if selected_gpu is not None and _probe_vulkan_environment(False, None):
                return RendererRuntime(
                    RendererMode.VULKAN,
                    notice=(
                        "The selected Vulkan GPU could not start, so pu6e Reloaded "
                        "is using Automatic GPU selection for this session."
                    ),
                )
            if _probe_vulkan_environment(True, None):
                return RendererRuntime(
                    RendererMode.VULKAN,
                    software_vulkan=True,
                    notice=(
                        "Hardware Vulkan is unavailable, so pu6e Reloaded is using "
                        "the CPU Vulkan renderer for this session."
                    ),
                )
            return RendererRuntime(
                RendererMode.OPENGL,
                notice=(
                    "Vulkan could not create a compatible graphics context. "
                    "pu6e Reloaded is using OpenGL for this session."
                ),
            )
        case unreachable:
            assert_never(unreachable)
