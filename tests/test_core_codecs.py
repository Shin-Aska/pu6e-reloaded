from contextlib import contextmanager
from typing import TYPE_CHECKING, Final

import pytest

from pu6e_core.formats.errors import FormatError
from pu6e_core.formats.npcs import decode_objlist, encode_objlist
from pu6e_core.formats.objects import decode_object_block, encode_object_block
from pu6e_core.formats.terrain import decode_chunks, decode_map, encode_chunks, encode_map
from pu6e_core.models.assets import ObjectCatalog
from pu6e_core.models.coordinates import pack_coords, unpack_coords
from pu6e_core.models.objects import (
    ContainmentError,
    ObjectPoint,
    PointAssignmentError,
    WorldObject,
)
from pu6e_core.services.editor import EditValueError

if TYPE_CHECKING:
    from collections.abc import Generator

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
def catalog() -> ObjectCatalog:
    return ObjectCatalog(tuple(range(1024)), (0,) * 7168, {})


@contextmanager
def _error_boundary() -> Generator[None]:
    yield


@pytest.mark.parametrize(
    "error",
    [
        FormatError("objblk", "truncated data", 8),
        ContainmentError("cyclic inventory"),
        PointAssignmentError(2),
        EditValueError("tile", 256, 255),
    ],
)
def test_typed_errors_propagate_through_context_managers(
    error: FormatError | ContainmentError | PointAssignmentError | EditValueError,
) -> None:
    with pytest.raises(type(error)) as caught, _error_boundary():
        raise error
    assert caught.value is error


@pytest.mark.parametrize(
    ("coordinates", "packed"),
    [
        ((0, 0, 0), (0, 0, 0)),
        ((1023, 1023, 15), (255, 255, 255)),
        ((256, 64, 1), (0, 1, 17)),
        ((0x123, 0x2AB, 5), (0x23, 0xAD, 0x5A)),
    ],
)
def test_coordinate_bytes_are_independent_vectors(
    coordinates: tuple[int, int, int],
    packed: tuple[int, int, int],
) -> None:
    assert pack_coords(*coordinates) == packed
    assert unpack_coords(*packed) == coordinates


def test_nested_object_roundtrip_preserves_order_unknown_bits_and_npc_aliases(
    catalog: ObjectCatalog,
) -> None:
    inventories: list[list[WorldObject]] = [[] for _ in range(256)]
    block = decode_object_block(_OBJECT_BLOCK, catalog, inventories)
    assert [(y, [x for x, _ in row]) for y, row in block] == [(7, [2]), (6, [9, 5])]
    point = block[1][1][1][1]
    assert [item.packed_type for item in point] == [4, 0x0401]
    chest = point[-1]
    child = chest.contains[0]
    assert (child.packed_type, child.status, child.y, child.z) == (0x0802, 0xC8, 8, 2)
    assert child.contains[0].packed_type == 3
    assert [item.packed_type for item in inventories[7]] == [0x0C07, 9]
    npcs = decode_objlist(bytes(0x600), catalog, inventories)
    assert npcs[7].contains is inventories[7]
    npc_point = ObjectPoint(20, 20, 0)
    npc_point.append(npcs[7])
    block.insert(0, (20, [(20, npc_point)]))
    assert encode_object_block(block) == _OBJECT_BLOCK
    assert (child.status, child.y, child.z) == (0xC8, 8, 2)
    assert [item.packed_type for item in point] == [4, 0x0401]


def test_large_container_indices_and_normalization_do_not_mutate_models(
    catalog: ObjectCatalog,
) -> None:
    parent = WorldObject(catalog, x=5, y=6, packed_type=1, quantity=2, quality=3)
    child = WorldObject(
        catalog, x=999, y=0xAB, z=3, status=0xD0, packed_type=0x0802, quantity=4, quality=5
    )
    parent.contains.append(child)
    point = ObjectPoint(5, 6, 0)
    point.append(parent)
    parent.status = 0xB9
    for _ in range(0x401):
        point.append(WorldObject(catalog))
    result = encode_object_block([(6, [(5, point)])])
    assert result[:2] == bytes.fromhex("03 04")
    assert result[-16:] == bytes.fromhex("a1 05 18 00 01 00 02 03 c8 01 a4 32 02 08 04 05")
    assert (parent.status, child.status, child.x, child.y) == (0xB9, 0xD0, 999, 0xAB)


def test_objlist_roundtrip_preserves_all_slots_frames_prefix_and_trailer(
    catalog: ObjectCatalog,
) -> None:
    source = bytearray(bytes(range(256)) + bytes(1280) + b"unknown\x00\xff")
    source[0x100:0x103] = bytes.fromhex("23 ad 5a")
    source[0x3FD:0x400] = bytes.fromhex("ff ff ff")
    source[0x400:0x402] = bytes.fromhex("ab ae")
    source[0x5FE:0x600] = bytes.fromhex("ff ff")
    npcs = decode_objlist(bytes(source), catalog, [[] for _ in range(256)])
    first, last = npcs[0], npcs[-1]
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
    assert encode_objlist(npcs, bytes(source[:0x100]), bytes(source[0x600:])) == source


def test_each_load_owns_npc_inventories_and_failed_decode_is_atomic(catalog: ObjectCatalog) -> None:
    first: list[list[WorldObject]] = [[] for _ in range(256)]
    second: list[list[WorldObject]] = [[] for _ in range(256)]
    _ = decode_object_block(_OBJECT_BLOCK, catalog, first)
    assert len(first[7]) == 2
    assert second[7] == []
    broken = bytes.fromhex("02 00 10 07 00 00 01 00 00 00 08 ff 0f 00 01 00 00 00")
    with pytest.raises(FormatError, match="must precede"):
        _ = decode_object_block(broken, catalog, second)
    assert second[7] == []


def test_terrain_roundtrip_preserves_12_bit_boundaries_and_chunk_bytes() -> None:
    source = bytearray(32256)
    source[:6] = bytes.fromhex("bc fa de ff 0f 00")
    source[24573:24579] = bytes.fromhex("23 c1 ab 56 f4 ff")
    source[-3:] = bytes.fromhex("00 f0 ff")
    terrain = decode_map(bytes(source))
    assert [len(block) for block in terrain] == [256] * 64 + [1024] * 5
    assert terrain[0][:4] == [0xABC, 0xDEF, 0xFFF, 0]
    assert terrain[63][-2:] == [0x123, 0xABC]
    assert terrain[64][:2] == [0x456, 0xFFF]
    assert terrain[68][-2:] == [0, 0xFFF]
    assert encode_map(terrain) == source
    chunks = bytes(range(64)) + bytes(reversed(range(64)))
    assert encode_chunks(decode_chunks(chunks)) == chunks


def test_malformed_inputs_and_unserializable_models_raise_format_errors(
    catalog: ObjectCatalog,
) -> None:
    with pytest.raises(FormatError, match="incomplete"):
        _ = decode_chunks(bytes(63))
    with pytest.raises(FormatError, match="expected 32256"):
        _ = decode_map(bytes(3))
    with pytest.raises(FormatError, match="requires at least"):
        _ = decode_objlist(bytes(1535), catalog, [[] for _ in range(256)])
    with pytest.raises(FormatError, match="expected 10"):
        _ = decode_object_block(bytes.fromhex("01 00"), catalog, [[] for _ in range(256)])
    point = ObjectPoint(0, 0, 0)
    item = WorldObject(catalog, quantity=256)
    point.append(item)
    with pytest.raises(FormatError, match="quantity"):
        _ = encode_object_block([(0, [(0, point)])])
    item.quantity = 0
    item.contains.append(item)
    with pytest.raises(FormatError, match="cycle"):
        _ = encode_object_block([(0, [(0, point)])])
