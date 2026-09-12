"""Ordered object-block codecs with explicit container and NPC relationships."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, assert_never

from pu6e_core.formats.errors import FormatError
from pu6e_core.models.coordinates import pack_coords, unpack_coords
from pu6e_core.models.objects import Npc, ObjectBlock, ObjectPoint, WorldObject

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pu6e_core.models.assets import ObjectCatalog


def decode_object_block(
    data: bytes,
    catalog: ObjectCatalog,
    npc_inventories: list[list[WorldObject]],
) -> ObjectBlock:
    """Rebuild drawing order and ownership, publishing inventories only on success."""
    count = _record_count(data, len(npc_inventories))
    block: ObjectBlock = []
    indexed: list[WorldObject] = []
    inventories: list[tuple[int, WorldObject]] = []
    for record_index in range(count):
        offset = 2 + record_index * 8
        item = _decode_record(data[offset : offset + 8], catalog, offset)
        if item.in_container():
            parent_index = item.x | ((item.y & 3) << 10)
            if parent_index >= len(indexed):
                raise FormatError(
                    "objblk", f"container {parent_index} must precede its contents", offset
                )
            indexed[parent_index].contains.append(item)
        elif item.in_inventory():
            if item.x >= 256:
                raise FormatError("objblk", f"invalid NPC inventory slot {item.x}", offset)
            inventories.append((item.x, item))
        else:
            _append_to_block(block, item)
        indexed.append(item)
    for _, row in block:
        for _, point in row:
            point.reverse()
        row.reverse()
    block.reverse()
    for npc_id, item in inventories:
        npc_inventories[npc_id].append(item)
    return block


def _record_count(data: bytes, inventory_count: int) -> int:
    if len(data) < 2:
        raise FormatError("objblk", "missing object count")
    count = int.from_bytes(data[:2], "little")
    if len(data) != 2 + count * 8:
        raise FormatError("objblk", f"expected {2 + count * 8} bytes, received {len(data)}")
    if inventory_count != 256:
        raise FormatError("objblk", "requires 256 NPC inventory lists")
    return count


def _append_to_block(block: ObjectBlock, item: WorldObject) -> None:
    if not block or block[-1][0] != item.y:
        block.append((item.y, []))
    row = block[-1][1]
    if not row or row[-1][0] != item.x:
        row.append((item.x, ObjectPoint(item.x, item.y, item.z)))
    row[-1][1].append(item)


def _decode_record(data: bytes, catalog: ObjectCatalog, offset: int) -> WorldObject:
    x, y, z = unpack_coords(data[1], data[2], data[3])
    packed_type = int.from_bytes(data[4:6], "little")
    if packed_type & 0x3FF >= len(catalog.base_tiles):
        raise FormatError("objblk", "object type has no catalog entry", offset)
    return WorldObject(catalog, x, y, z, data[0], packed_type, data[6], data[7])


@dataclass(frozen=True, slots=True)
class _PendingObject:
    item: WorldObject
    parent: WorldObject | None
    parent_index: int


def _top_level(block: ObjectBlock) -> Iterable[WorldObject]:
    for _, row in reversed(block):
        for _, point in reversed(row):
            yield from reversed(point)


def encode_object_block(block: ObjectBlock) -> bytes:
    """Flatten object trees without emitting NPC records or mutating model fields."""
    result = bytearray()
    count = 0
    seen: set[int] = set()
    pending = [_PendingObject(item, None, -1) for item in reversed(list(_top_level(block)))]
    while pending:
        entry = pending.pop()
        item = entry.item
        if id(item) in seen:
            raise FormatError("objblk", "object occurs more than once or forms a containment cycle")
        seen.add(id(item))
        own_index = count
        if not item.is_npc():
            result.extend(_encode_record(entry))
            count += 1
            if count > 0xFFFF:
                raise FormatError("objblk", "object count does not fit 16 bits")
        pending.extend(_PendingObject(child, item, own_index) for child in reversed(item.contains))
    return count.to_bytes(2, "little") + result


def _encode_record(entry: _PendingObject) -> bytes:
    item, parent = entry.item, entry.parent
    x, y, z, status = item.x, item.y, item.z, item.status
    match parent:
        case None:
            status &= ~0x18
        case Npc(npc_id=npc_id):
            if not 0 <= npc_id < 256:
                raise FormatError("objblk", f"invalid NPC inventory slot {npc_id}")
            x = npc_id
            if not status & 0x10:
                status = (status | 0x10) & ~0x08
        case WorldObject():
            if not 0 <= entry.parent_index <= 0xFFF:
                raise FormatError("objblk", "container index does not fit 12 bits")
            status = (status & ~0x10) | 0x08
            x = entry.parent_index & 0x3FF
            y = (y & ~3) | (entry.parent_index >> 10 & 3)
        case _:
            assert_never(parent)
    for field, value, maximum in (
        ("status", status, 255),
        ("packed_type", item.packed_type, 0xFFFF),
        ("quantity", item.quantity, 255),
        ("quality", item.quality, 255),
    ):
        if not 0 <= value <= maximum:
            raise FormatError("objblk", f"{field} value {value} exceeds its wire field")
    return (
        bytes((status, *pack_coords(x, y, z)))
        + item.packed_type.to_bytes(2, "little")
        + bytes((item.quantity, item.quality))
    )
