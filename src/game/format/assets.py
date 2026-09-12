"""Decode immutable artwork, font, and text assets from installation resources."""

from types import MappingProxyType
from typing import TYPE_CHECKING, Final, assert_never

from game.format.errors import FormatError
from game.format.resources import decode_resource
from game.models.assets import (
    AnimationData,
    FontData,
    HybridMask,
    ObjectCatalog,
    Palette,
    TileSet,
    WorldAssets,
)
from game.models.game import GameType

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

# These tile-index byte pointers are taken from u6mcga.drv.
_HYBRID_SOURCES: Final = (
    0x16,
    0x16,
    0x1A,
    0x1A,
    0x1E,
    0x1E,
    0x12,
    0x12,
    0x1A,
    0x1E,
    0x16,
    0x12,
    0x16,
    0x1A,
    0x1E,
    0x12,
    0x1A,
    0x1E,
    0x1E,
    0x12,
    0x12,
    0x16,
    0x16,
    0x1A,
    0x12,
    0x16,
    0x1E,
    0x1A,
    0x1A,
    0x1E,
    0x12,
    0x16,
)


def decode_palette(data: bytes) -> Palette:
    """Convert 256 six-bit VGA RGB triples, making the final color black."""
    if len(data) < 768:
        raise FormatError("palette", "expected 768 bytes")
    colors = tuple(
        (data[index] << 2, data[index + 1] << 2, data[index + 2] << 2)
        for index in range(0, 765, 3)
    )
    return Palette((*colors, (0, 0, 0)))


def decode_words(data: bytes, resource: str = "word table") -> tuple[int, ...]:
    """Decode little-endian unsigned words, rejecting a trailing partial word."""
    if len(data) % 2:
        raise FormatError(resource, "incomplete 16-bit value")
    return tuple(
        int.from_bytes(data[index : index + 2], "little")
        for index in range(0, len(data), 2)
    )


def decode_animation(data: bytes) -> AnimationData:
    """Decode the count and four fixed-length animation control tables."""
    if len(data) < 194:
        raise FormatError("animdata", "expected 194 bytes")
    count = int.from_bytes(data[:2], "little")
    if count > 32:
        raise FormatError("animdata", f"invalid animation count {count}")
    return AnimationData(
        count,
        decode_words(data[2:66]),
        decode_words(data[66:130]),
        tuple(data[130:162]),
        tuple(data[162:194]),
    )


def _compressed_tile(data: bytes, offset: int) -> tuple[bytes, int]:
    if offset >= len(data):
        raise FormatError("tiles", "missing compressed tile length", offset)
    length = data[offset] * 16
    end = offset + length
    if length == 0 or end > len(data):
        raise FormatError("tiles", "invalid compressed tile length", offset)
    cursor = offset + 1
    pixels = bytearray(b"\xff" * 256)
    tile_index = 0
    while cursor < end:
        if cursor + 3 > end:
            raise FormatError("tiles", "truncated pixel run", cursor)
        displacement = int.from_bytes(data[cursor : cursor + 2], "little")
        run_length = data[cursor + 2]
        cursor += 3
        if run_length == 0:
            break
        tile_index += displacement % 160 + (160 if displacement >= 1760 else 0)
        if cursor + run_length > end or tile_index + run_length > 256:
            raise FormatError("tiles", "pixel run exceeds its tile", cursor)
        pixels[tile_index : tile_index + run_length] = data[
            cursor : cursor + run_length
        ]
        tile_index += run_length
        cursor += run_length
    return bytes(pixels), end


def decode_tiles(data: bytes, masktypes: bytes) -> tuple[bytes, ...]:
    """Decode sequential raw or run-compressed 16 by 16 indexed tiles."""
    tiles: list[bytes] = []
    offset = 0
    for mask in masktypes[:0x800]:
        if mask == 0x0A:
            tile, offset = _compressed_tile(data, offset)
        else:
            if offset + 256 > len(data):
                raise FormatError("tiles", "truncated raw tile", offset)
            tile = data[offset : offset + 256]
            offset += 256
        tiles.append(tile)
    return tuple(tiles)


def decode_hybrids(data: bytes) -> tuple[HybridMask, ...]:
    """Expand the 32 control blocks to the legacy RGBA-channel mask layout."""
    if not data:
        return ()
    if len(data) != 32 * 64:
        raise FormatError("animmask", "expected 32 masks of 64 bytes")
    hybrids: list[HybridMask] = []
    for index, source in enumerate(_HYBRID_SOURCES):
        mask = bytearray(1024)
        pixel = 0
        for cursor in range(index * 64, (index + 1) * 64, 2):
            count, displacement = data[cursor] * 4, data[cursor + 1] * 4
            if pixel + count > len(mask):
                raise FormatError("animmask", "mask run exceeds 256 pixels", cursor)
            mask[pixel : pixel + count] = bytes((1,)) * count
            if displacement == 0:
                break
            pixel += count + displacement
        hybrids.append(HybridMask(index + 16, source // 2, bytes(mask)))
    return tuple(hybrids)


def decode_names(data: bytes) -> Mapping[int, str]:
    """Decode null-terminated DOS descriptions keyed by their final tile frame."""
    names: dict[int, str] = {}
    cursor = 0
    while cursor < len(data):
        tile = int.from_bytes(data[cursor : cursor + 2], "little")
        # LOOK may end with the tile index beyond its final 0x800 description.
        if tile == 0x801 and cursor + 2 == len(data):
            break
        end = data.find(b"\0", cursor + 2)
        if cursor + 2 > len(data) or end < 0:
            raise FormatError("look", "truncated description", cursor)
        names[tile] = data[cursor + 2 : end].decode("cp437")
        cursor = end + 1
    return MappingProxyType(names)


def decode_books(data: bytes) -> tuple[str, ...]:
    """Ignore the 256-byte index and decode complete DOS text strings."""
    return tuple(value.decode("cp437") for value in data[256:].split(b"\0")[:-1])


def decode_font(data: bytes) -> FontData:
    """Parse the complete 256-character monochrome font bitmap."""
    if len(data) != 2048:
        raise FormatError("font", "expected 256 glyphs of eight bytes")
    return FontData(data)


def load_assets(directory: Path, game: GameType) -> WorldAssets:
    """Read a complete independent collection of immutable installation assets."""
    palette = decode_palette(decode_resource(directory, game, "palette"))
    flags = tuple(decode_resource(directory, game, "tileflag"))
    tiles = TileSet(
        decode_tiles(
            decode_resource(directory, game, "maptiles")
            + decode_resource(directory, game, "objtiles"),
            decode_resource(directory, game, "masktypes"),
        ),
        flags,
        decode_words(decode_resource(directory, game, "tileindx"), "tileindx"),
        decode_animation(decode_resource(directory, game, "animdata")),
        decode_hybrids(decode_resource(directory, game, "animmask")),
    )
    catalog = ObjectCatalog(
        decode_words(decode_resource(directory, game, "basetile"), "basetile"),
        flags,
        decode_names(decode_resource(directory, game, "look")),
    )
    try:
        font = decode_font(decode_resource(directory, game, "font"))
    except FileNotFoundError:
        font = None
    match game:
        case GameType.FP:
            books = decode_books(decode_resource(directory, game, "books"))
        case GameType.MD | GameType.SE:
            books = ("",) * 128
        case _:
            assert_never(game)
    return WorldAssets(palette, tiles, catalog, font, books)
