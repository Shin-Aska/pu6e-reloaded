from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from game.format.npcs import decode_objlist
from game.format.objects import encode_object_block
from game.models.coordinates import pack_coords, unpack_coords
from game.models.objects import ObjectPoint, WorldObject
from game.services.loader import WorldLoader
from game.services.saver import WorldSaver
from game_fixtures import write_game_fixture

if TYPE_CHECKING:
    from pathlib import Path


_COORDINATES: Final = (
    ((0, 0, 0), (0x00, 0x00, 0x00)),
    ((1023, 1023, 15), (0xFF, 0xFF, 0xFF)),
    ((256, 64, 1), (0x00, 0x01, 0x11)),
    ((0x123, 0x2AB, 5), (0x23, 0xAD, 0x5A)),
    ((255, 63, 0), (0xFF, 0xFC, 0x00)),
)
# Records 0/3 share a world stack; 1/2 nest under container indices 0/1.
# Record 6 is readied NPC 7 inventory, with record 7 inside container index 6.
_OBJECT_BLOCK: Final = bytes.fromhex("""
    09 00
    a1 05 18 00 01 04 02 42
    c8 00 20 20 02 08 03 43
    08 01 00 00 03 00 04 44
    40 05 18 00 04 00 05 45
    00 09 18 00 05 00 01 46
    00 02 1c 00 06 00 01 47
    98 07 30 10 07 0c 06 48
    28 06 10 30 08 00 07 49
    10 07 00 00 09 00 08 4a
""")


@pytest.fixture
def game_directory(tmp_path: Path) -> Path:
    game_dir = tmp_path / "game"
    write_game_fixture(game_dir, "fp", "fixture")
    return game_dir


@pytest.mark.parametrize(
    ("coordinates", "packed"),
    [
        *_COORDINATES,
        ((1024, 1024, 16), (0, 0, 0)),
        ((-1, -1, -1), (255, 255, 255)),
    ],
)
def test_pack_coordinates_preserves_only_10_10_4_bits(
    coordinates: tuple[int, int, int],
    packed: tuple[int, int, int],
) -> None:
    assert pack_coords(*coordinates) == packed


@pytest.mark.parametrize(("coordinates", "packed"), _COORDINATES)
def test_unpack_coordinates_decodes_independent_byte_vectors(
    coordinates: tuple[int, int, int],
    packed: tuple[int, int, int],
) -> None:
    assert unpack_coords(*packed) == coordinates


def test_objblk_read_restores_drawing_order_and_nested_inventory(game_directory: Path) -> None:
    _ = (game_directory / "savegame/objblkaa").write_bytes(_OBJECT_BLOCK)

    session = WorldLoader.load(game_directory, "fp")

    assert [(y, [x for x, _ in row]) for y, row in session.state.object_blocks[0]] == [
        (7, [2]),
        (6, [9, 5]),
    ]
    stack = session.editor.objects_at(5, 6, 0)
    assert stack is not None
    assert [item.packed_type for item in stack] == [4, 0x0401]
    chest = stack[-1]
    assert (chest.status, chest.quantity, chest.quality) == (0xA1, 2, 0x42)
    contained = chest.contains[0]
    assert (contained.packed_type, contained.status, contained.y, contained.z) == (
        0x0802,
        0xC8,
        8,
        2,
    )
    assert contained.in_container()
    assert [item.packed_type for item in contained.contains] == [3]
    inventory = session.state.npcs[7].contains
    assert [item.packed_type for item in inventory] == [0x0C07, 9]
    assert inventory[0].status == 0x98
    assert inventory[0].in_inventory()
    assert not inventory[0].in_container()
    assert [(item.packed_type, item.status) for item in inventory[0].contains] == [(8, 0x28)]


def test_objblk_write_flattens_nested_inventory_without_serializing_npc(
    game_directory: Path,
) -> None:
    _ = (game_directory / "savegame/objblkaa").write_bytes(_OBJECT_BLOCK)
    session = WorldLoader.load(game_directory, "fp")
    npc = session.state.npcs[7]
    inventory = npc.contains
    npc.set_type(0x100)
    session.editor.add_object_at(npc, 20, 20, 0)

    output = encode_object_block(session.state.object_blocks[0])

    assert output == _OBJECT_BLOCK
    stack = session.editor.objects_at(5, 6, 0)
    assert stack is not None
    assert [item.packed_type for item in stack] == [4, 0x0401]
    assert npc.contains is inventory


def test_object_writer_encodes_high_container_index_and_normalizes_flags(
    game_directory: Path,
) -> None:
    catalog = WorldLoader.load(game_directory, "fp").state.assets.catalog
    parent = WorldObject(catalog, x=5, y=6, z=0, packed_type=1, quantity=2, quality=3)
    child = WorldObject(
        catalog, x=999, y=0xAB, z=3, status=0xD0, packed_type=0x0802, quantity=4, quality=5
    )
    parent.contains.append(child)
    point = ObjectPoint(5, 6, 0)
    point.append(parent)
    parent.status = 0xB9
    for _ in range(0x401):
        point.append(WorldObject(catalog))

    output = encode_object_block([(6, [(5, point)])])

    assert output[:2] == bytes.fromhex("03 04")
    assert output[2:-16] == bytes.fromhex("00 05 18 00 00 00 00 00") * 0x401
    assert output[-16:] == bytes.fromhex("a1 05 18 00 01 00 02 03 c8 01 a4 32 02 08 04 05")
    assert (parent.status, child.status, child.x, child.y) == (0xB9, 0xD0, 999, 0xAB)


def test_npc_objlist_reads_all_256_slots_and_six_bit_frames(game_directory: Path) -> None:
    catalog = WorldLoader.load(game_directory, "fp").state.assets.catalog
    source = bytearray(1536)
    source[0x100:0x103] = bytes.fromhex("23 ad 5a")
    source[0x3FD:0x400] = bytes.fromhex("ff ff ff")
    source[0x400:0x402] = bytes.fromhex("ab ae")
    source[0x5FE:0x600] = bytes.fromhex("ff ff")

    npcs = decode_objlist(bytes(source), catalog, [[] for _ in range(256)])

    assert len(npcs) == 256
    first, last = npcs[0], npcs[255]
    assert (first.npc_id, first.x, first.y, first.z, first.base_type, first.frame()) == (
        0,
        0x123,
        0x2AB,
        5,
        0x2AB,
        43,
    )
    assert (last.npc_id, last.x, last.y, last.z, last.base_type, last.frame()) == (
        255,
        1023,
        1023,
        15,
        1023,
        63,
    )


def test_npc_save_preserves_objlist_prefix_tail_and_original_backup(game_directory: Path) -> None:
    source = bytes(range(256)) + bytes(1280) + b"unparsed-save-data\x00\xff"
    path = game_directory / "savegame/objlist"
    _ = path.write_bytes(source)
    session = WorldLoader.load(game_directory, "fp")
    npc = session.state.npcs[255]
    npc.x, npc.y, npc.z = 0x123, 0x2AB, 5
    npc.set_type(0x2AB)
    npc.set_frame(43)
    expected = bytearray(source)
    expected[0x3FD:0x400] = bytes.fromhex("23 ad 5a")
    expected[0x5FE:0x600] = bytes.fromhex("ab ae")

    _ = WorldSaver.save(session)

    assert path.read_bytes() == bytes(expected)
    assert path.with_suffix(".bak").read_bytes() == source


def test_map_reads_12_bit_chunk_ids_at_surface_and_dungeon_boundaries(game_directory: Path) -> None:
    source = bytearray(32256)
    source[:6] = bytes.fromhex("bc fa de ff 0f 00")
    source[24573:24579] = bytes.fromhex("23 c1 ab 56 f4 ff")
    source[-3:] = bytes.fromhex("00 f0 ff")
    _ = (game_directory / "map").write_bytes(source)

    terrain = WorldLoader.load(game_directory, "fp").state.terrain

    assert [len(block) for block in terrain.superchunks] == [256] * 64 + [1024] * 5
    assert terrain.superchunks[0][:4] == [0xABC, 0xDEF, 0xFFF, 0]
    assert terrain.superchunks[63][-2:] == [0x123, 0xABC]
    assert terrain.superchunks[64][:2] == [0x456, 0xFFF]
    assert terrain.superchunks[68][-2:] == [0, 0xFFF]


def test_map_save_writes_12_bit_pairs_and_backup_when_dirty(game_directory: Path) -> None:
    session = WorldLoader.load(game_directory, "fp")
    session.editor.set_chunk(0xABC, 0, 0, 0)
    session.editor.set_chunk(0xDEF, 8, 0, 0)
    session.editor.set_chunk(0xFFF, 248, 248, 5)
    assert session.state.terrain.map_dirty
    expected = bytearray(32256)
    expected[:3] = bytes.fromhex("bc fa de")
    expected[-3:] = bytes.fromhex("00 f0 ff")

    _ = WorldSaver.save(session)

    assert (game_directory / "map").read_bytes() == bytes(expected)
    assert (game_directory / "map.bak").read_bytes() == bytes(32256)
    assert not session.state.terrain.map_dirty
    assert not (game_directory / "chunks.bak").exists()


def test_chunk_save_persists_dirty_tiles_without_rewriting_map(game_directory: Path) -> None:
    source = bytes(range(64)) + bytes(reversed(range(64)))
    _ = (game_directory / "chunks").write_bytes(source)
    session = WorldLoader.load(game_directory, "fp")
    session.state.terrain.superchunks[0][0] = 1
    session.editor.set_map_tile(0xFE, 3, 4, 0)
    assert session.state.terrain.chunks_dirty
    expected = bytearray(source)
    expected[64 + 35] = 0xFE

    _ = WorldSaver.save(session)

    assert (game_directory / "chunks").read_bytes() == bytes(expected)
    assert (game_directory / "chunks.bak").read_bytes() == source
    assert not session.state.terrain.chunks_dirty
    assert not (game_directory / "map.bak").exists()
