"""NPC slot codecs retaining bytes outside the documented objlist section."""

from typing import TYPE_CHECKING, Final

from pu6e_core.formats.errors import FormatError
from pu6e_core.models.coordinates import pack_coords, unpack_coords
from pu6e_core.models.objects import Npc, WorldObject

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pu6e_core.models.assets import ObjectCatalog

NPC_COUNT: Final = 256
PREFIX_SIZE: Final = 0x100
KNOWN_END: Final = 0x600


def decode_objlist(
    data: bytes,
    catalog: ObjectCatalog,
    npc_inventories: list[list[WorldObject]],
) -> list[Npc]:
    """Decode 256 NPC slots and bind each slot to its supplied inventory list."""
    if len(data) < KNOWN_END:
        raise FormatError("objlist", f"requires at least {KNOWN_END} bytes, received {len(data)}")
    if len(npc_inventories) != NPC_COUNT:
        raise FormatError("objlist", "requires 256 NPC inventory lists")
    result: list[Npc] = []
    for npc_id in range(NPC_COUNT):
        offset = PREFIX_SIZE + npc_id * 3
        x, y, z = unpack_coords(*data[offset : offset + 3])
        offset = 0x400 + npc_id * 2
        packed_type = int.from_bytes(data[offset : offset + 2], "little")
        if packed_type & 0x3FF >= len(catalog.base_tiles):
            raise FormatError("objlist", "object type has no catalog entry", offset)
        result.append(
            Npc(
                catalog=catalog,
                x=x,
                y=y,
                z=z,
                packed_type=packed_type,
                contains=npc_inventories[npc_id],
                npc_id=npc_id,
            )
        )
    return result


def encode_objlist(npcs: Sequence[Npc], prefix: bytes, trailer: bytes) -> bytes:
    """Serialize NPC fields without changing the preserved prefix or trailing data."""
    if len(npcs) != NPC_COUNT:
        raise FormatError("objlist", f"requires 256 NPC slots, received {len(npcs)}")
    if len(prefix) != PREFIX_SIZE:
        raise FormatError("objlist", "prefix must contain exactly 256 bytes")
    coordinates = bytearray()
    types = bytearray()
    for npc_id, npc in enumerate(npcs):
        if npc.npc_id != npc_id:
            raise FormatError("objlist", f"slot {npc_id} contains NPC {npc.npc_id}")
        if not 0 <= npc.packed_type <= 0xFFFF:
            raise FormatError("objlist", f"NPC {npc_id} object type does not fit 16 bits")
        coordinates.extend(pack_coords(npc.x, npc.y, npc.z))
        types.extend(npc.packed_type.to_bytes(2, "little"))
    return prefix + coordinates + types + trailer
