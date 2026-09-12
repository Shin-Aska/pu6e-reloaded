"""Immutable game artwork and catalog values, independent of rendering and I/O."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

type RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class Palette:
    """RGB colors shared by sessions without renderer animation mutations."""

    colors: tuple[RGB, ...]

    def tobytes(self) -> bytes:
        """Flatten RGB colors for image conversion and texture uploads."""
        return bytes(channel for color in self.colors for channel in color)

    def rotated(self, length: int, *entries: int) -> Palette:
        """Move the final color of each requested cycle to its beginning."""
        colors = list(self.colors)
        for entry in entries:
            colors.insert(entry, colors.pop(entry + length - 1))
        return Palette(tuple(colors))


@dataclass(frozen=True, slots=True)
class AnimationData:
    """Fixed tile animation tables decoded from animdata."""

    num_tiles: int
    tiles: tuple[int, ...]
    first_frames: tuple[int, ...]
    and_masks: tuple[int, ...]
    shift_values: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class HybridMask:
    """Tile pair and RGBA-channel mask used for water animation compositing."""

    destination: int
    source: int
    mask: bytes


@dataclass(frozen=True, slots=True)
class TileSet:
    """Indexed pixel data, flags, and controls for all installation tiles."""

    pixels: tuple[bytes, ...]
    flags: tuple[int, ...]
    index: tuple[int, ...]
    animations: AnimationData
    hybrids: tuple[HybridMask, ...]


@dataclass(frozen=True, slots=True)
class ObjectCatalog:
    """Immutable object definitions used to interpret every world object."""

    base_tiles: tuple[int, ...]
    tile_flags: tuple[int, ...]
    names: Mapping[int, str]

    def __post_init__(self) -> None:
        """Retain an immutable snapshot of the caller's catalog descriptions."""
        # A mapping proxy must own its backing mapping, not wrap caller state.
        object.__setattr__(self, "names", MappingProxyType(dict(self.names)))

    def tile_for_type(self, packed_type: int) -> int:
        """Resolve the base type and animation frame packed into one word."""
        return self.base_tiles[packed_type & 0x3FF] + (packed_type >> 10)

    def name_for_tile(self, tile: int) -> str | None:
        """Find the description stored on the final frame of a tile range."""
        return next(
            (self.names[index] for index in range(tile, 0x801) if index in self.names),
            None,
        )

    def article(self, tile: int) -> str:
        """Return the indefinite or definite article selected by tile flags."""
        return ("", "a", "an", "the")[(self.tile_flags[0x1400 + tile] >> 6) & 3]

    def size(self, tile: int) -> int:
        """Return width and height extension bits, in bits one and zero."""
        return (self.tile_flags[0x800 + tile] >> 6) & 3

    def height(self, tile: int) -> int:
        """Return whether the tile is drawn above normal-height objects."""
        return (self.tile_flags[0x800 + tile] >> 4) & 1

    def weight(self, base_type: int) -> int:
        """Return object weight in tenths, before quantity adjustments."""
        return self.tile_flags[0x1000 + base_type]

    def lowest_look(self, tile: int) -> bool:
        """Return whether look and use prioritize other overlapping tiles."""
        return bool(self.tile_flags[0x1400 + tile] & 0x10)

    def is_blocked(self, tile: int) -> bool:
        """Return the tile's movement-blocking flag."""
        return bool(self.tile_flags[tile] & 2)

    def force_passable(self, tile: int) -> bool:
        """Return whether an object overrides the terrain's blocking flag."""
        return bool(self.tile_flags[0x1400 + tile] & 4)


@dataclass(frozen=True, slots=True)
class FontData:
    """The monochrome eight-by-eight bitmap for each DOS character."""

    bitmap: bytes

    def character(self, char: int, transparent: bool = False) -> bytes:
        """Expand the glyph left-to-right, with the VGA font color indices."""
        off = 0 if transparent else 0x31
        return bytes(
            0x48 if row & (0x80 >> bit) else off
            for row in self.bitmap[char * 8 : (char + 1) * 8]
            for bit in range(8)
        )


@dataclass(frozen=True, slots=True)
class WorldAssets:
    """A session's immutable installation artwork and object descriptions."""

    palette: Palette
    tiles: TileSet
    catalog: ObjectCatalog
    font: FontData | None
    books: tuple[str, ...]
