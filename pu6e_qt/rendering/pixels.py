"""Pure indexed-pixel expansion and palette-cycle construction."""

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from pu6e_core.models.assets import Palette


TRANSPARENT_INDEX: Final = 255
PALETTE_CYCLE_START: Final = 0xE0
PALETTE_CYCLE_END: Final = 0xFB


def indexed_to_rgba(data: bytes, palette: Palette, *, opaque: bool = False) -> tuple[bytes, bool]:
    """Expand pixels and report whether they reference a cycling palette range."""
    rgba = bytearray()
    animated = False
    for index in data:
        rgba.extend(palette.colors[index])
        rgba.append(255 if opaque or index != TRANSPARENT_INDEX else 0)
        animated |= PALETTE_CYCLE_START <= index <= PALETTE_CYCLE_END
    return bytes(rgba), animated


def palette_cycles(palette: Palette) -> tuple[Palette, ...]:
    """Build eight immutable frames for the VGA palette cycles."""
    rotations: list[Palette] = []
    for step in range(8):
        rotations.append(palette)
        palette = palette.rotated(8, 0xE0, 0xE8)
        if step & 1:
            palette = palette.rotated(4, 0xF0, 0xF4, 0xF8)
    return tuple(rotations)


def fontchar_to_rgba(mask: bytes) -> bytes:
    """Expand the game font mask to white opaque or transparent RGBA pixels."""
    return b"".join(bytes((255, 255, 255, 255)) if pixel else bytes(4) for pixel in mask)
