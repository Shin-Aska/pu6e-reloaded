"""Behavior checks for immutable game assets and binary artwork decoding."""

from struct import pack
from typing import TYPE_CHECKING

import pytest

from game.format.assets import (
    decode_animation,
    decode_books,
    decode_font,
    decode_hybrids,
    decode_names,
    decode_palette,
    decode_tiles,
    decode_words,
)
from game.format.errors import FormatError
from game.format.lzw import decompress_buffer
from game.format.resources import (
    decode_resource,
    palette_filename,
    required_game_files,
    resolve_dos_path,
)
from game.models.assets import FontData, ObjectCatalog, Palette

if TYPE_CHECKING:
    from pathlib import Path


def test_palette_rotation_returns_independent_value() -> None:
    original = Palette(((1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12)))
    rotated = original.rotated(3, 0)
    assert rotated.colors == ((7, 8, 9), (1, 2, 3), (4, 5, 6), (10, 11, 12))
    assert original.tobytes() == bytes(range(1, 13))


def test_catalog_copies_names_and_resolves_last_frame() -> None:
    names = {4: "sword"}
    catalog = ObjectCatalog((2,), tuple(bytes(0x1800)), names)
    names[4] = "changed"
    assert catalog.tile_for_type(2 << 10) == 4
    assert catalog.name_for_tile(2) == "sword"
    assert catalog.name_for_tile(5) is None


def test_catalog_decodes_tile_attribute_bits() -> None:
    flags = bytearray(0x1800)
    flags[7] = 2
    flags[0x807] = 0xD0
    flags[0x1002] = 35
    flags[0x1407] = 0x94
    catalog = ObjectCatalog((0,), tuple(flags), {})
    assert (
        catalog.article(7),
        catalog.size(7),
        catalog.height(7),
        catalog.weight(2),
    ) == (
        "an",
        3,
        1,
        35,
    )
    assert catalog.lowest_look(7)
    assert catalog.is_blocked(7)
    assert catalog.force_passable(7)


def test_font_expands_high_bit_first_with_optional_transparency() -> None:
    font = FontData(bytes((0x81,)) + bytes(2047))
    assert (
        font.character(0)
        == bytes((0x48,)) + bytes((0x31,)) * 6 + bytes((0x48,)) + bytes((0x31,)) * 56
    )
    assert font.character(0, transparent=True) == bytes((0x48,)) + bytes(6) + bytes(
        (0x48,)
    ) + bytes(56)


def test_palette_converts_vga_channels_and_transparent_background() -> None:
    palette = decode_palette(bytes((1, 2, 63)) * 256)
    assert palette.colors[0] == (4, 8, 252)
    assert palette.colors[-1] == (0, 0, 0)
    assert len(palette.tobytes()) == 768


def test_animation_decodes_fixed_tables() -> None:
    animation = decode_animation(
        pack("<H", 2)
        + pack("<32H", *range(32))
        + pack("<32H", *range(32, 64))
        + bytes(range(64))
    )
    assert animation.num_tiles == 2
    assert animation.tiles == tuple(range(32))
    assert animation.first_frames == tuple(range(32, 64))
    assert animation.and_masks == tuple(range(32))
    assert animation.shift_values == tuple(range(32, 64))


def test_tiles_keep_compressed_displacement_and_following_raw_tile_aligned() -> None:
    compressed = b"\x01" + pack("<HB", 1761, 2) + b"\x7f\x80" + bytes(10)
    decoded = decode_tiles(compressed + bytes((42,)) * 256, b"\x0a\x00")
    expected = bytearray(b"\xff" * 256)
    expected[161:163] = b"\x7f\x80"
    assert decoded == (bytes(expected), bytes((42,)) * 256)


def test_hybrids_expand_control_bytes_without_flipping_orientation() -> None:
    controls = bytes((2, 3, 1, 0)) + bytes(60)
    hybrids = decode_hybrids(controls + bytes(31 * 64))
    assert len(hybrids) == 32
    assert (hybrids[0].destination, hybrids[0].source) == (16, 11)
    assert (hybrids[-1].destination, hybrids[-1].source) == (47, 11)
    assert hybrids[0].mask == bytes((1,)) * 8 + bytes(12) + bytes((1,)) * 4 + bytes(
        1000
    )
    assert decode_hybrids(b"") == ()


def test_dos_text_decoders_preserve_codepage_and_completed_records() -> None:
    assert decode_names(pack("<H", 42) + b"caf\x82\0")[42] == "caf\u00e9"
    assert decode_books(bytes(256) + b"first\0caf\x82\0unterminated") == (
        "first",
        "caf\u00e9",
    )


def test_names_accept_terminal_tile_index_without_description() -> None:
    source = pack("<H", 42) + b"sword\0" + pack("<H", 0x801)
    assert decode_names(source) == {42: "sword"}


@pytest.mark.parametrize("source", [b"\x2a", pack("<H", 42) + b"truncated"])
def test_names_reject_incomplete_nonterminal_record(source: bytes) -> None:
    with pytest.raises(FormatError, match="truncated description"):
        _ = decode_names(source)


def test_font_parser_rejects_incomplete_glyph_table() -> None:
    with pytest.raises(FormatError, match="256 glyphs"):
        _ = decode_font(bytes(2047))


def test_word_parser_rejects_partial_word() -> None:
    with pytest.raises(FormatError, match="16-bit"):
        _ = decode_words(b"\x01")


def test_tile_parser_rejects_runs_past_fixed_tile_size() -> None:
    malformed = b"\x01" + pack("<HB", 1919, 2) + b"xx" + bytes(10)
    with pytest.raises(FormatError, match="exceeds"):
        _ = decode_tiles(malformed, b"\x0a")


def test_lzw_decodes_dictionary_reference() -> None:
    codes = (0x100, 65, 66, 0x102, 0x101)
    packed_codes = sum(code << (index * 9) for index, code in enumerate(codes))
    compressed = pack("<I", 4) + packed_codes.to_bytes(6, "little")
    assert decompress_buffer(compressed) == b"ABAB"


def test_lzw_rejects_truncated_stream() -> None:
    with pytest.raises(FormatError, match="truncated"):
        _ = decompress_buffer(pack("<I", 4) + b"\x00\x83")


@pytest.mark.parametrize(
    ("game", "palette", "look", "book"),
    [
        ("fp", "u6pal", "look.lzd", True),
        ("md", "mdpal", "look.lzc", False),
        ("se", "sepal", "look.lzc", False),
    ],
)
def test_manifests_list_complete_required_files(
    game: str, palette: str, look: str, book: bool
) -> None:
    files = required_game_files(game)
    assert palette_filename(game) == palette
    assert {palette, look, "basetile", "map", "chunks", "savegame/objlist"} <= set(
        files
    )
    assert len([name for name in files if name.startswith("savegame/objblk")]) == 69
    assert ("book.dat" in files) is book
    assert "u6.ch" not in files


def test_library_resource_skips_declared_header_and_resolves_disk_case(
    tmp_path: Path,
) -> None:
    path = tmp_path / "LOOK.LZC"
    _ = path.write_bytes(pack("<IH", 13, 9) + b"hdr" + b"data")
    assert resolve_dos_path(tmp_path / "look.lzc").name == "LOOK.LZC"
    assert decode_resource(tmp_path, "md", "look") == b"data"


def test_empty_resource_does_not_require_file(tmp_path: Path) -> None:
    assert decode_resource(tmp_path, "se", "animmask") == b""


def test_library_resource_rejects_inconsistent_size(tmp_path: Path) -> None:
    _ = (tmp_path / "look.lzc").write_bytes(pack("<IH", 99, 6))
    with pytest.raises(FormatError, match="file size"):
        _ = decode_resource(tmp_path, "md", "look")
