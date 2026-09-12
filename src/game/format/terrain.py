"""Byte codecs for 12-bit chunk references and 8 by 8 terrain chunks."""

from typing import TYPE_CHECKING, Final

from game.format.errors import FormatError

if TYPE_CHECKING:
    from collections.abc import Sequence

MAP_BYTES: Final = 32256
CHUNK_BYTES: Final = 64


def decode_map(data: bytes) -> list[list[int]]:
    """Decode 64 surface superchunks followed by five dungeon superchunks."""
    if len(data) != MAP_BYTES:
        raise FormatError("map", f"expected {MAP_BYTES} bytes, received {len(data)}")
    result: list[list[int]] = []
    offset = 0
    for block in range(69):
        count = 256 if block < 64 else 1024
        entries: list[int] = []
        for _ in range(count // 2):
            b0, b1, b2 = data[offset : offset + 3]
            entries.extend((b0 | ((b1 & 15) << 8), (b1 >> 4) | (b2 << 4)))
            offset += 3
        result.append(entries)
    return result


def encode_map(superchunks: Sequence[Sequence[int]]) -> bytes:
    """Pack each pair of twelve-bit chunk references into three bytes."""
    if len(superchunks) != 69:
        raise FormatError("map", f"expected 69 superchunks, received {len(superchunks)}")
    result = bytearray()
    for block, entries in enumerate(superchunks):
        count = 256 if block < 64 else 1024
        if len(entries) != count:
            raise FormatError("map", f"superchunk {block} requires {count} entries")
        for index in range(0, count, 2):
            first, second = entries[index : index + 2]
            if not 0 <= first <= 0xFFF or not 0 <= second <= 0xFFF:
                raise FormatError("map", "chunk reference does not fit 12 bits", len(result))
            result.extend((first & 255, (first >> 8) | ((second & 15) << 4), second >> 4))
    return bytes(result)


def decode_chunks(data: bytes) -> list[bytearray]:
    """Return independently editable 64-byte terrain chunks."""
    if len(data) % CHUNK_BYTES:
        raise FormatError(
            "chunks", "incomplete 64-byte chunk", len(data) // CHUNK_BYTES * CHUNK_BYTES
        )
    return [
        bytearray(data[index : index + CHUNK_BYTES]) for index in range(0, len(data), CHUNK_BYTES)
    ]


def encode_chunks(chunks: Sequence[bytearray]) -> bytes:
    """Join complete terrain chunks without modifying their bytearrays."""
    for index, chunk in enumerate(chunks):
        if len(chunk) != CHUNK_BYTES:
            raise FormatError("chunks", f"chunk {index} requires {CHUNK_BYTES} bytes")
    return b"".join(chunks)
