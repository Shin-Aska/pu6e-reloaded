from __future__ import annotations

import configparser
from enum import StrEnum
from pathlib import Path
from typing import Final, assert_never


class RendererMode(StrEnum):
    SOFTWARE = "software"
    OPENGL = "opengl"
    VULKAN = "vulkan"

    @property
    def label(self) -> str:
        match self:
            case RendererMode.SOFTWARE:
                return "Software"
            case RendererMode.OPENGL:
                return "OpenGL"
            case RendererMode.VULKAN:
                return "Vulkan"
            case unreachable:
                assert_never(unreachable)

    @property
    def description(self) -> str:
        match self:
            case RendererMode.SOFTWARE:
                return "Maximum compatibility using the CPU-based Mesa renderer."
            case RendererMode.OPENGL:
                return "Native desktop OpenGL for the best default performance."
            case RendererMode.VULKAN:
                return "Vulkan through Mesa Zink while preserving the classic map renderer."
            case unreachable:
                assert_never(unreachable)


RENDERER_MODES: Final = tuple(RendererMode)


def read_renderer_mode(config_path: Path) -> RendererMode:
    configuration = configparser.ConfigParser()
    try:
        configuration.read(config_path, encoding="utf-8")
    except configparser.Error:
        return RendererMode.OPENGL
    value = configuration.get("launcher", "renderer", fallback=None)
    if value is None:
        return RendererMode.VULKAN
    try:
        return RendererMode(value)
    except ValueError:
        return RendererMode.OPENGL
