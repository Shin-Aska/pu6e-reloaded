from pathlib import Path
from struct import pack

import pytest

from pu6e_core.formats import lzw
from pu6e_core.formats.assets import (
    decode_books,
    decode_names,
    decode_palette,
    decode_tiles,
    decode_words,
)
from pu6e_core.formats.errors import FormatError
from pu6e_core.formats.terrain import decode_chunks
from pu6e_core.models.assets import ObjectCatalog, Palette
from pu6e_core.models.coordinates import adjust_coords_for_level, world_to_chunk
from pu6e_core.models.game import GameType
from pu6e_core.models.objects import ObjectPoint, WorldObject
from pu6e_core.services.loader import WorldLoader
from pu6e_qt.rendering import batch
from pu6e_qt.rendering.pixels import fontchar_to_rgba, indexed_to_rgba
from tests.game_fixtures import pack_codes, write_game_fixture


def test_lzw_decompresses_dictionary_references() -> None:
    compressed = pack("<I", 4) + pack_codes([0x100, ord("A"), ord("B"), 0x102, 0x101])
    assert lzw.is_valid_lzw_buffer(compressed)
    assert lzw.decompress_buffer(compressed) == b"ABAB"


def test_lzw_rejects_invalid_input() -> None:
    with pytest.raises(FormatError, match="not a valid"):
        _ = lzw.decompress_buffer(b"invalid")


def test_map_round_trip_and_coordinate_helpers() -> None:
    original = [bytearray(range(64)), bytearray([255] * 64)]

    chunks = decode_chunks(b"".join(bytes(chunk) for chunk in original))

    assert chunks == original
    assert adjust_coords_for_level(0x3F, 0x21, 0, 1) == (0x0F, 0x09, 1)
    assert world_to_chunk(1025, 1026, 0) == (0, 0, 0, 0, 1, 2)


def test_text_resources_decode_dos_codepage() -> None:
    names = decode_names(pack("<H", 42) + b"caf\x82\0")
    books = decode_books(bytes(256) + b"first\0second\0")

    assert names[42] == "café"
    assert books == ("first", "second")


def test_palette_parsing_and_bytes() -> None:
    source = b"".join(bytes((i % 64, i % 64, i % 64)) for i in range(256))

    palette = decode_palette(source)

    assert len(palette.tobytes()) == 256 * 3
    assert palette.colors[1] == (4, 4, 4)
    assert palette.colors[-1] == (0, 0, 0)


def test_tile_index_uses_integer_word_count() -> None:
    index = decode_words(pack("<3H", 1, 2, 65535))

    assert index == (1, 2, 65535)


def test_compressed_tile_run_preserves_fixed_tile_size() -> None:
    compressed_tile = b"\x01" + pack("<HB", 1, 1) + b"\x7f" + bytes(11)

    tiles = decode_tiles(compressed_tile, bytes((0x0A,)))

    assert len(tiles[0]) == 256
    assert tiles[0][1] == 0x7F


def test_palette_conversion_reports_animation() -> None:
    palette = Palette(tuple((index, index, index) for index in range(256)))

    rgba, animated = indexed_to_rgba(bytes((1, 0xE0, 0xFF)), palette)

    assert rgba == bytes((1, 1, 1, 255, 0xE0, 0xE0, 0xE0, 255, 0xFF, 0xFF, 0xFF, 0))
    assert animated


def test_draw_object_block_renders_large_object_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, int, int, int]] = []

    def capture_part(texture: int, x: int, y: int, z: int) -> None:
        calls.append((texture, x, y, z))

    monkeypatch.setattr(batch, "draw_poly_tex", capture_part)
    flags = [0] * 0x1600
    flags[0x800 + 12] = 3 << 6
    catalog = ObjectCatalog(tuple(range(32)), tuple(flags), {})
    point = ObjectPoint(4, 5, 0)
    point.append(WorldObject(catalog, packed_type=12))

    batch.draw_objblk(0, 4, 5, 16, 16, 0, 128, 128, [[(5, [(4, point)])]], list(range(32)), catalog)

    assert calls == [
        (12, 16, 16, 0),
        (11, 0, 16, 0),
        (10, 16, 0, 0),
        (9, 0, 0, 0),
    ]


def test_loader_sets_session_game_configuration(tmp_path: Path) -> None:
    directory = tmp_path / "se"
    write_game_fixture(directory, "se", "savage empire")

    session = WorldLoader.load(directory, "se")

    assert session.state.game_type is GameType.SE
    assert session.state.game_dir == directory.resolve()
    assert session.state.assets.catalog.name_for_tile(0) == "savage empire"


@pytest.mark.parametrize(
    ("game", "label"),
    [("fp", "false prophet"), ("md", "martian dreams"), ("se", "savage empire")],
)
def test_loader_loads_complete_fixture_for_each_supported_game(
    tmp_path: Path,
    game: str,
    label: str,
) -> None:
    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, label)

    state = WorldLoader.load(game_dir, game).state

    assert state.game_type == GameType(game)
    assert state.assets.catalog.name_for_tile(0) == label
    assert len(state.assets.tiles.pixels) == 2048
    assert len(state.terrain.superchunks) == 69
    assert len(state.terrain.chunks) == 1
    assert len(state.object_blocks) == 69
    assert len(state.npcs) == 256
    assert state.assets.palette.colors[0] == (4, 4, 4)


def test_loader_preserves_working_directory_when_loading_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    game_dir = tmp_path / "incomplete-game"
    game_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        _ = WorldLoader.load(game_dir, "fp")

    assert Path.cwd() == tmp_path


def test_missing_font_remains_independent_of_previous_game_data(tmp_path: Path) -> None:
    with_font, without_font = tmp_path / "with-font", tmp_path / "without-font"
    write_game_fixture(with_font, "se", "first")
    write_game_fixture(without_font, "se", "second")
    _ = (with_font / "u6.ch").write_bytes(b"\x80" + bytes(2047))
    previous = WorldLoader.load(with_font, "se")

    current = WorldLoader.load(without_font, "se")

    assert current.state.assets.font is None
    assert previous.state.assets.font is not None
    assert previous.state.assets.font.bitmap == b"\x80" + bytes(2047)


def test_font_mask_expands_to_complete_rgba_pixels() -> None:
    mask = bytes((0, 1)) + bytes(62)

    rgba = fontchar_to_rgba(mask)

    assert len(rgba) == 8 * 8 * 4
    assert rgba[:4] == bytes(4)
    assert rgba[4:8] == bytes((255, 255, 255, 255))
