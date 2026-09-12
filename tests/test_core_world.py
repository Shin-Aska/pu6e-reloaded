from pathlib import Path

import pytest

from game.models.assets import AnimationData, ObjectCatalog, Palette, TileSet, WorldAssets
from game.models.game import GameType
from game.models.objects import ContainmentError, Npc, WorldObject
from game.models.world import WorldMap, WorldState
from game.services.session import WorldSession


def make_session(flags: tuple[int, ...] = (0,) * 7168) -> WorldSession:
    catalog = ObjectCatalog(tuple(range(1024)), flags, {1: "helm", 8: "loa/f\\ves"})
    assets = WorldAssets(
        Palette(((0, 0, 0),) * 256),
        TileSet((bytes(256),) * 2048, flags, (), AnimationData(0, (), (), (), ()), ()),
        catalog,
        None,
        (),
    )
    terrain = WorldMap(
        [[0] * (256 if block < 64 else 1024) for block in range(69)],
        [bytearray(64), bytearray([1] * 64)],
    )
    return WorldSession(
        WorldState(GameType.FP, Path("game"), terrain, [[] for _ in range(69)], [], assets)
    )


def test_simultaneous_world_edits_and_dirty_state_are_independent() -> None:
    first, second = make_session(), make_session()
    item = first.editor.new_object()
    assert item.packed_type == 1
    first.editor.add_object_at(item, 5, 6, 0)
    first.editor.set_map_tile(14, 3, 4, 0)
    first.editor.set_chunk(1, 8, 0, 0)
    assert first.editor.move_object(item, 128, 130, 0)

    assert first.state.dirty_object_blocks == {0, 9}
    assert first.editor.map_tile_at(3, 4, 0) == 14
    assert first.editor.chunk_at(8, 0, 0) == (1, 0, 0)
    assert first.state.terrain.map_dirty
    assert first.state.terrain.chunks_dirty
    assert second.editor.map_tile_at(3, 4, 0) == 0
    assert second.editor.chunk_at(8, 0, 0) == (0, 0, 0)
    assert second.editor.objects_at(128, 130, 0) is None
    assert not second.state.dirty_object_blocks
    assert not second.state.terrain.map_dirty
    assert not second.state.terrain.chunks_dirty
    assert not second.editor.move_object(item, 1, 1, 0)
    first.editor.clear_changes()
    assert not first.state.dirty_object_blocks
    assert not first.state.terrain.map_dirty
    assert not first.state.terrain.chunks_dirty


def test_object_points_order_and_replacements_normalize_child_placement() -> None:
    session = make_session()
    editor = session.editor
    for x, y in ((5, 6), (9, 6), (2, 7), (1, 6)):
        editor.add_object_at(editor.new_object(), x, y, 0)
    assert [(y, [x for x, _ in row]) for y, row in session.state.object_blocks[0]] == [
        (7, [2]),
        (6, [9, 5, 1]),
    ]
    point = editor.point_at(5, 6, 0)
    replacement = WorldObject(session.state.assets.catalog, x=99, y=99, z=5, status=0xFF)
    point[0] = replacement
    assert (replacement.x, replacement.y, replacement.z, replacement.status) == (5, 6, 0, 0xE7)
    extra = editor.new_object()
    extra.status = 0x18
    point[:] = [extra, replacement]
    assert point[:] == [extra, replacement]
    assert (extra.x, extra.y, extra.z, extra.status) == (5, 6, 0, 0)
    point.reverse()
    assert point[:] == [replacement, extra]
    assert editor.objects_at(5, 6, 0) is point
    assert editor.remove_object(extra, 5, 6, 0)
    assert point[:] == [replacement]


def test_inventory_clone_keeps_catalog_and_copies_child_identities() -> None:
    session = make_session()
    parent = session.editor.new_object()
    child = session.editor.new_object()
    parent.insert(0, child)
    cloned = parent.clone()
    assert cloned is not None
    assert cloned is not parent
    assert cloned.catalog is parent.catalog
    assert cloned.contains[0] is not child
    assert cloned.contains[0].catalog is child.catalog
    cloned.contains[0].quantity = 9
    assert child.quantity == 0
    assert child.in_container()
    assert child.y == 0
    with pytest.raises(ContainmentError):
        child.insert(0, parent)
    npc = Npc(session.state.assets.catalog, npc_id=7)
    with pytest.raises(ContainmentError):
        parent.insert(0, npc)
    npc.insert(0, cloned)
    assert cloned.status & 0x18 == 0x10
    assert npc.clone() is None
    assert npc.weight() == npc.weight_total() == 0


def test_placing_npc_preserves_all_coordinate_bits_on_dungeon_levels() -> None:
    session = make_session()
    npc = Npc(session.state.assets.catalog, x=0x123, y=0x2AB, z=5, packed_type=1, npc_id=7)
    session.editor.add_object_at(npc, npc.x, npc.y, npc.z)
    assert (npc.x, npc.y, npc.z) == (0x123, 0x2AB, 5)
    point = session.editor.objects_at(npc.x, npc.y, npc.z)
    assert point is not None
    assert point[0] is npc


def test_object_name_weight_and_type_share_one_packed_source() -> None:
    flags = [0] * 7168
    flags[0x1400 + 8] = 0x40
    flags[0x1000 + 8] = 12
    session = make_session(tuple(flags))
    item = WorldObject(session.state.assets.catalog, packed_type=8, quantity=1)
    assert item.name() == "1 loaf"
    item.quantity = 4
    assert item.name() == "4 loaves"
    assert item.weight_total() == 48
    item.set_frame(43)
    assert item.base_type == 8
    assert item.frame() == 43
    assert item.packed_type == 0xAC08
    assert item.tile == 51
    item.set_type(1)
    assert item.frame() == 0
    assert item.tile == 1
    assert item.num_frames() == 1
    assert bool(item)


def test_look_and_collision_include_wrapped_large_object_parts() -> None:
    flags = [0] * 7168
    flags[0x800 + 5] = 0x80
    flags[4] = 2
    session = make_session(tuple(flags))
    item = WorldObject(session.state.assets.catalog, packed_type=5)
    session.editor.add_object_at(item, 0, 6, 0)
    assert session.editor.lookable_at(1023, 6, 0) is item
    assert session.editor.is_blocked(1023, 6, 0)
    assert not session.editor.is_blocked(1022, 6, 0)


def test_force_passable_objects_override_terrain_but_blocking_objects_win() -> None:
    flags = [0] * 7168
    flags[0] = flags[3] = 2
    flags[0x1400 + 2] = 4
    session = make_session(tuple(flags))
    assert session.editor.is_blocked(5, 6, 0)
    session.editor.add_object_at(WorldObject(session.state.assets.catalog, packed_type=2), 5, 6, 0)
    assert not session.editor.is_blocked(5, 6, 0)
    blocker = WorldObject(session.state.assets.catalog, packed_type=3)
    session.editor.add_object_at(blocker, 5, 6, 0)
    assert session.editor.is_blocked(5, 6, 0)
    assert session.editor.lookable_at(5, 6, 0) is blocker
