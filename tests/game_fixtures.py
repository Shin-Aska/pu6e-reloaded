from collections.abc import Sequence
from pathlib import Path
from struct import pack


def pack_codes(codes: Sequence[int], width: int = 9) -> bytes:
    output = bytearray()
    buffer = 0
    buffered_bits = 0
    for code in codes:
        buffer |= code << buffered_bits
        buffered_bits += width
        while buffered_bits >= 8:
            output.append(buffer & 0xFF)
            buffer >>= 8
            buffered_bits -= 8
    if buffered_bits:
        output.append(buffer)
    return bytes(output)


def encode_lzw_literals(data: bytes) -> bytes:
    codes: list[int] = []
    for offset in range(0, len(data), 200):
        codes.append(0x100)
        codes.extend(data[offset:offset + 200])
    codes.append(0x101)
    return pack("<I", len(data)) + pack_codes(codes)


def write_game_fixture(game_dir: Path, game: str, label: str) -> None:
    game_dir.mkdir()
    palette_name = {"fp": "u6pal", "md": "mdpal", "se": "sepal"}[game]
    (game_dir / palette_name).write_bytes(bytes((1,)) * 768)
    (game_dir / "tileflag").write_bytes(bytes(0x1800))
    (game_dir / "tileindx.vga").write_bytes(bytes(0x1000))
    (game_dir / "animdata").write_bytes(bytes(194))
    (game_dir / "objtiles.vga").write_bytes(bytes(1792 * 256))
    (game_dir / "chunks").write_bytes(bytes(64))
    (game_dir / "map").write_bytes(bytes(32256))
    (game_dir / "basetile").write_bytes(bytes(2048))
    savegame = game_dir / "savegame"
    savegame.mkdir()
    (savegame / "objlist").write_bytes(bytes(1536))
    for y in "abcdefgh":
        for x in "abcdefgh":
            (savegame / f"objblk{x}{y}").write_bytes(bytes(2))
    for x in "abcde":
        (savegame / f"objblk{x}i").write_bytes(bytes(2))

    look_data = pack("<H", 0) + label.encode("ascii") + b"\0"
    masktypes = bytes(0x800)
    maptiles = bytes(256 * 256)
    if game == "fp":
        (game_dir / "look.lzd").write_bytes(encode_lzw_literals(look_data))
        (game_dir / "masktype.vga").write_bytes(encode_lzw_literals(masktypes))
        (game_dir / "maptiles.vga").write_bytes(encode_lzw_literals(maptiles))
        (game_dir / "animmask.vga").write_bytes(encode_lzw_literals(bytes(32 * 64)))
        (game_dir / "book.dat").write_bytes(bytes(256))
    else:
        def library(data: bytes) -> bytes:
            return pack("<IH", len(data) + 6, 6) + data

        (game_dir / "look.lzc").write_bytes(library(look_data))
        (game_dir / "masktype.vga").write_bytes(library(masktypes))
        (game_dir / "maptiles.vga").write_bytes(library(maptiles))
