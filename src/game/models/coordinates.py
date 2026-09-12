"""Pure coordinate conversions retaining the game's packed bit layout."""


def pack_coords(x: int, y: int, z: int) -> tuple[int, int, int]:
    """Pack coordinates, retaining the low 10, 10, and 4 bits respectively."""
    return x & 0xFF, (x >> 8 & 3) | (y << 2 & 0xFC), (y >> 6 & 15) | (z << 4 & 0xF0)


def unpack_coords(h: int, d1: int, d2: int) -> tuple[int, int, int]:
    """Recover the complete stored coordinates, including the upper level bits."""
    return ((d1 & 3) << 8) | h, ((d2 & 15) << 6) | (d1 >> 2 & 63), d2 >> 4 & 15


def wrap_coords(wx: int, wy: int, wz: int) -> tuple[int, int, int]:
    """Wrap coordinates to the selected world's dimensions and six levels."""
    width = 1024 if wz == 0 else 256
    return wx % width, wy % width, wz % 6


def adjust_coords_for_level(
    wx: int,
    wy: int,
    wz: int,
    newz: int,
    quality: int = 0,
) -> tuple[int, int, int]:
    """Map between surface and dungeon chunks using the exit quality offsets."""
    newz %= 6
    if wz == 0 and newz > 0:
        wx, wy = _down(wx), _down(wy)
    elif wz > 0 and newz == 0:
        wx, wy = _up(wx, quality & 3), _up(wy, quality >> 2 & 3)
    return wx, wy, newz


def _down(value: int) -> int:
    return (value & 7) | (value >> 2 & 0xF8)


def _up(value: int, offset: int) -> int:
    return (value & 7) | (value << 2 & 0x3E0) | (offset << 2 & 0x0C)


def world_to_chunk(x: int, y: int, z: int) -> tuple[int, int, int, int, int, int]:
    """Return superchunk, chunk, and tile coordinate pairs, wrapping x and y."""
    if z == 0:
        return x >> 7 & 7, y >> 7 & 7, x >> 3 & 15, y >> 3 & 15, x & 7, y & 7
    return z - 1, 8, x >> 3 & 31, y >> 3 & 31, x & 7, y & 7


def world_to_block(wx: int, wy: int, wz: int) -> int:
    """Select the object block for a world coordinate using legacy address masks."""
    if wz == 0:
        return ((wx & 1023) >> 7) + ((wy & 1023) >> 7) * 8
    return 63 + (wz & 7)


def block_to_world(block: int) -> tuple[int, int, int]:
    """Return the upper-left world coordinate of an object block."""
    if block < 64:
        return (block & 7) * 128, (block >> 3) * 128, 0
    return 0, 0, block - 63


def block_num_to_id(block: int) -> str:
    """Return the two-letter DOS suffix for an object block number."""
    if block < 64:
        return chr(ord("a") + block % 8) + chr(ord("a") + block // 8)
    return chr(ord("a") + block - 64) + "i"
