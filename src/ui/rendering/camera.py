"""Framebuffer-space camera transforms with a stable wrapped world center."""

from __future__ import annotations

from dataclasses import dataclass
from math import floor, isfinite
from typing import override


class InvalidZoomError(ValueError):
    """A requested camera scale cannot define finite screen-to-world transforms."""

    def __init__(self, scale: float) -> None:
        self.scale: float = scale
        super().__init__(scale)

    @override
    def __str__(self) -> str:
        return f"camera zoom must be finite and positive, got {self.scale}"


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class CameraState:
    """Mutable controller-owned camera; all screen coordinates use framebuffer pixels."""

    position: tuple[int, int, int] = (0, 0, 0)
    scale: float = 1.0
    width: int = 0
    height: int = 0

    def __post_init__(self) -> None:
        self.set_position(*self.position)
        self.set_zoom(self.scale)
        self.resize(self.width, self.height)

    @property
    def center_offset(self) -> tuple[int, int]:
        """Tile offset from the viewport origin to its center."""
        return floor(self.width / self.scale / 32), floor(self.height / self.scale / 32)

    @property
    def world_size(self) -> int:
        """Width and height of the current world level in tiles."""
        return 1024 if self.position[2] == 0 else 256

    @property
    def coords(self) -> tuple[int, int, int]:
        """Wrapped world tile at the upper-left viewport corner."""
        x, y, z = self.position
        offset_x, offset_y = self.center_offset
        return (x - offset_x) % self.world_size, (y - offset_y) % self.world_size, z

    def set_position(self, x: int, y: int, z: int) -> None:
        """Center the camera on a wrapped tile and level."""
        z %= 6
        size = 1024 if z == 0 else 256
        self.position = x % size, y % size, z

    def resize(self, width: int, height: int) -> None:
        """Update framebuffer bounds while retaining the world center."""
        self.width, self.height = max(0, width), max(0, height)

    def set_zoom(self, scale: float) -> None:
        """Apply a finite positive scale while retaining the world center."""
        if not isfinite(scale) or scale <= 0:
            raise InvalidZoomError(scale)
        self.scale = scale

    def screen_to_world(self, x: float, y: float) -> tuple[int, int, int]:
        """Resolve framebuffer pixels to a wrapped world tile, including negative pixels."""
        world_x, world_y, z = self.coords
        return (
            (world_x + floor(x / 16 / self.scale)) % self.world_size,
            (world_y + floor(y / 16 / self.scale)) % self.world_size,
            z,
        )

    def world_to_screen(self, x: int, y: int) -> tuple[float, float]:
        """Return the first wrapped occurrence at or after the viewport origin."""
        world_x, world_y, _ = self.coords
        return (
            (x - world_x) % self.world_size * 16 * self.scale,
            (y - world_y) % self.world_size * 16 * self.scale,
        )
