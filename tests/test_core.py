from io import BytesIO
from pathlib import Path
from struct import pack

import pytest

from U6 import Map, book, look, lzw, pal, tile


def pack_codes(codes, width=9):
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


def encode_lzw_literals(data):
    codes = []
    for offset in range(0, len(data), 200):
        codes.append(0x100)
        codes.extend(data[offset:offset + 200])
    codes.append(0x101)
    return pack("<I", len(data)) + pack_codes(codes)


def write_game_fixture(game_dir, game, label):
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
        def library(data):
            return pack("<IH", len(data) + 6, 6) + data

        (game_dir / "look.lzc").write_bytes(library(look_data))
        (game_dir / "masktype.vga").write_bytes(library(masktypes))
        (game_dir / "maptiles.vga").write_bytes(library(maptiles))


def test_lzw_decompresses_dictionary_references():
    compressed = pack("<I", 4) + pack_codes([0x100, ord("A"), ord("B"), 0x102, 0x101])
    assert lzw.is_valid_lzw_buffer(compressed)
    assert lzw.decompress_buffer(compressed) == b"ABAB"


def test_lzw_rejects_invalid_input():
    with pytest.raises(ValueError, match="not a valid"):
        lzw.decompress_buffer(b"invalid")


def test_map_round_trip_and_coordinate_helpers(tmp_path):
    original = [list(range(64)), [255] * 64]
    Map.parse_chunks(BytesIO(b"".join(bytes(chunk) for chunk in original)))
    assert Map.chunks == original
    assert Map.adjust_coords_for_level(0x3F, 0x21, 0, 1) == (0x0F, 0x09, 1)
    assert Map.world_to_chunk(1025, 1026, 0) == (0, 0, 0, 0, 1, 2)


def test_text_resources_decode_dos_codepage():
    look.parse(pack("<H", 42) + b"caf\x82\0")
    assert look.get_obj_name(42) == "café"
    book.parse(bytes(256) + b"first\0second\0")
    assert book.books == ["first", "second"]


def test_palette_parsing_and_bytes():
    source = b"".join(bytes((i % 64, i % 64, i % 64)) for i in range(256))
    palette = pal.pal()
    palette.parse(BytesIO(source))
    assert len(palette.tobytes()) == 256 * 3
    assert palette.pal[1] == (4, 4, 4)
    assert palette.pal[-1] == (0, 0, 0)


def test_tile_index_uses_integer_word_count():
    tile.parse_tileindx(pack("<3H", 1, 2, 65535))
    assert tile.tileindx == (1, 2, 65535)


def test_compressed_tile_run_preserves_fixed_tile_size():
    tile.masktypes = (0x0A,)
    compressed_tile = b"\x01" + pack("<HB", 1, 1) + b"\x7f" + bytes(11)

    tile.parse_maptiles(compressed_tile)

    assert len(tile.maptiles[0]) == 256
    assert tile.maptiles[0][1] == 0x7F


def test_fastgl_palette_conversion_reports_animation():
    import fastgl

    palette = bytes(channel for index in range(256) for channel in (index, index, index))
    rgba, animated = fastgl.indexed_to_rgba(bytes((1, 0xE0, 0xFF)), palette)
    assert rgba == bytes((1, 1, 1, 255, 0xE0, 0xE0, 0xE0, 255, 0xFF, 0xFF, 0xFF, 0))
    assert animated == 1


def test_fastgl_draw_object_block_renders_large_object_parts(monkeypatch):
    from types import SimpleNamespace

    import fastgl

    calls = []
    monkeypatch.setattr(fastgl, "draw_poly_tex", lambda *args: calls.append(args))
    flags = [0] * 0x1600
    flags[0x800 + 12] = 3 << 6
    objects = [[(5, [(4, [SimpleNamespace(tile=12)])])]]
    textures = list(range(32))

    fastgl.draw_objblk(0, 4, 5, 16, 16, 0, 128, 128, objects, textures, flags)

    assert calls == [
        (12, 16, 16, 0),
        (11, 0, 16, 0),
        (10, 16, 0, 0),
        (9, 0, 0, 0),
    ]


def test_read_data_sets_runtime_game_configuration(monkeypatch, tmp_path):
    import mapedit_gl
    from U6 import Config

    calls = []
    monkeypatch.setattr(mapedit_gl.pal.pal, "read", lambda self, game: calls.append(("pal", game)))
    for module in (mapedit_gl.book, mapedit_gl.look, mapedit_gl.tile, mapedit_gl.Map,
                   mapedit_gl.obj, mapedit_gl.NPCs, mapedit_gl.Font):
        monkeypatch.setattr(module, "read", lambda *args, _name=module.__name__: calls.append((_name, args)))
    monkeypatch.setattr(mapedit_gl.NPCs, "populate", lambda: calls.append(("populate", ())))

    mapedit_gl.read_data(tmp_path, "se")

    assert Config.gametype == "se"
    assert Config.gamedir == str(tmp_path.resolve())
    assert calls


@pytest.mark.parametrize(
    ("game", "label"),
    (("fp", "false prophet"), ("md", "martian dreams"), ("se", "savage empire")),
)
def test_read_data_loads_complete_fixture_for_each_supported_game(tmp_path, game, label):
    import mapedit_gl
    from U6 import Config, NPCs, obj

    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, label)

    mapedit_gl.read_data(game_dir, game)

    assert Config.gametype == game
    assert look.get_obj_name(0) == label
    assert len(tile.maptiles) == 2048
    assert len(Map.map) == 69
    assert len(Map.chunks) == 1
    assert len(obj.objblk) == 69
    assert len(NPCs.npcs) == 256
    assert mapedit_gl.palette.pal[0] == (4, 4, 4)


def test_read_data_restores_working_directory_when_loading_fails(monkeypatch, tmp_path):
    import mapedit_gl

    game_dir = tmp_path / "incomplete-game"
    game_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        mapedit_gl.read_data(game_dir, "fp")

    assert Path.cwd() == tmp_path


def test_missing_font_clears_previous_game_data(monkeypatch, tmp_path):
    from U6 import Font

    monkeypatch.chdir(tmp_path)
    Font.chardata = object()

    assert Font.read("se") == 0
    assert Font.chardata is None


def test_font_mask_expands_to_complete_rgba_pixels():
    import numpy
    import mapedit_gl

    mask = numpy.zeros(64, dtype=numpy.uint8)
    mask[1] = 1
    rgba = mapedit_gl.fontchar_to_rgba(mask)

    assert len(rgba) == 8 * 8 * 4
    assert rgba[:4] == bytes(4)
    assert rgba[4:8] == bytes((255, 255, 255, 255))
