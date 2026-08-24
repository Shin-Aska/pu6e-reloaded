"""Ultima VI LZW decompression implemented in pure Python."""

from __future__ import annotations


def get_uncompressed_size_buffer(data: bytes) -> int:
    """Return the little-endian output size stored in an LZW header."""
    if len(data) < 4:
        return -1
    return int.from_bytes(data[:4], "little")


def is_valid_lzw_buffer(data: bytes) -> bool:
    """Check the inexpensive invariants present in an Ultima VI LZW stream."""
    return len(data) >= 6 and data[3] == 0 and data[4] == 0 and data[5] & 1 == 1


def decompress_buffer(data: bytes) -> bytes:
    """Decompress an Ultima VI LZW buffer, including its four-byte size header."""
    if not is_valid_lzw_buffer(data):
        raise ValueError("not a valid Ultima VI LZW buffer")
    expected = get_uncompressed_size_buffer(data)
    source = data[4:] + b"\0\0"
    bit_offset = 0
    width = 9
    next_code = 0x102
    limit = 0x200
    table: dict[int, bytes] = {}
    output = bytearray()
    previous = b""

    def read_code() -> int:
        nonlocal bit_offset
        byte = bit_offset // 8
        value = int.from_bytes(source[byte : byte + 3], "little")
        value = (value >> (bit_offset % 8)) & ((1 << width) - 1)
        bit_offset += width
        return value

    while True:
        code = read_code()
        if code == 0x101:
            break
        if code == 0x100:
            table.clear()
            width, next_code, limit = 9, 0x102, 0x200
            code = read_code()
            if code > 0xFF:
                raise ValueError("invalid first code after dictionary reset")
            entry = bytes((code,))
            output.extend(entry)
            previous = entry
            continue

        if code < 0x100:
            entry = bytes((code,))
        elif code in table:
            entry = table[code]
        elif code == next_code and previous:
            entry = previous + previous[:1]
        else:
            raise ValueError(f"invalid LZW code 0x{code:x}")

        output.extend(entry)
        if previous:
            table[next_code] = previous + entry[:1]
            next_code += 1
            if next_code >= limit and width < 12:
                width += 1
                limit *= 2
        previous = entry
        if len(output) > expected:
            raise ValueError("LZW stream exceeds its declared output size")

    if len(output) != expected:
        raise ValueError(f"LZW output is {len(output)} bytes; expected {expected}")
    return bytes(output)
