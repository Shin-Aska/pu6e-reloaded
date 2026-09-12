"""Complete installation loading and recoverable on-disk save behavior."""

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from game.models.game import GameType
from game.services.loader import WorldLoader
from game.services.saver import WorldSaver
from game_fixtures import write_game_fixture

if TYPE_CHECKING:
    from game.services.session import WorldSession


@pytest.fixture
def loaded_world(tmp_path: Path) -> WorldSession:
    game_dir = tmp_path / "world"
    write_game_fixture(game_dir, "fp", "fixture")
    return WorldLoader.load(game_dir, "fp")


@pytest.mark.parametrize("game", ["fp", "md", "se"])
def test_loader_reads_complete_independent_game_fixture(
    tmp_path: Path, game: str
) -> None:
    game_dir = tmp_path / game
    write_game_fixture(game_dir, game, game)
    original_cwd = Path.cwd()

    session = WorldLoader.load(game_dir, game)

    assert session.state.game_type == GameType(game)
    assert session.state.game_dir == game_dir.resolve()
    assert len(session.state.object_blocks) == 69
    assert len(session.state.npcs) == 256
    assert len(session.state.terrain.superchunks) == 69
    assert len(session.state.assets.tiles.pixels) == 2048
    assert session.state.assets.catalog.name_for_tile(0) == game
    assert session.state.assets.palette.colors[0] == (4, 4, 4)
    assert session.state.assets.font is None
    assert not session.state.dirty_object_blocks
    assert Path.cwd() == original_cwd


def test_edits_and_reloads_do_not_share_world_state(loaded_world: WorldSession) -> None:
    second = WorldLoader.load(loaded_world.state.game_dir, "fp")
    third = WorldLoader.load(loaded_world.state.game_dir, "fp")

    second.editor.set_map_tile(45, 0, 0, 0)
    second.editor.add_object_at(second.editor.new_object(), 5, 6, 0)

    assert (
        loaded_world.editor.map_tile_at(0, 0, 0)
        == third.editor.map_tile_at(0, 0, 0)
        == 0
    )
    assert not loaded_world.editor.objects_at(5, 6, 0)
    assert not third.editor.objects_at(5, 6, 0)
    assert second.state.terrain.chunks_dirty
    assert not loaded_world.state.terrain.chunks_dirty


def test_failed_load_leaves_callers_previous_session_untouched(
    loaded_world: WorldSession, tmp_path: Path
) -> None:
    game_dir = tmp_path / "broken"
    write_game_fixture(game_dir, "se", "broken")
    (game_dir / "savegame/objblkei").unlink()
    loaded_world.editor.set_map_tile(91, 0, 0, 0)

    with pytest.raises(FileNotFoundError):
        _ = WorldLoader.load(game_dir, "se")

    assert loaded_world.editor.map_tile_at(0, 0, 0) == 91
    assert loaded_world.state.assets.catalog.name_for_tile(0) == "fixture"
    assert loaded_world.state.terrain.chunks_dirty


def test_loader_populates_only_valid_npcs_and_keeps_shared_inventories(
    tmp_path: Path,
) -> None:
    game_dir = tmp_path / "npcs"
    write_game_fixture(game_dir, "fp", "fixture")
    objlist = bytearray(1536)
    objlist[0x100:0x103] = bytes((5, 24, 0))
    objlist[0x103:0x106] = bytes((7, 32, 0x60))
    objlist[0x400:0x404] = bytes((1, 0, 2, 0))
    _ = (game_dir / "savegame/objlist").write_bytes(objlist)
    _ = (game_dir / "savegame/objblkaa").write_bytes(
        bytes.fromhex("01 00 10 00 00 00 03 00 01 00")
    )
    _ = (game_dir / "savegame/objblkei").write_bytes(
        bytes.fromhex("01 00 10 00 00 00 04 00 01 00")
    )

    session = WorldLoader.load(game_dir, "fp")

    npc = session.state.npcs[0]
    point = session.editor.objects_at(5, 6, 0)
    assert point is not None
    assert list(point) == [npc]
    assert [item.packed_type for item in npc.contains] == [3, 4]
    assert not session.editor.objects_at(7, 8, 0)
    assert session.state.npcs[1].z == 6
    assert not session.state.dirty_object_blocks


def test_save_always_backs_up_objlist_and_preserves_unparsed_bytes(
    loaded_world: WorldSession,
) -> None:
    path = loaded_world.state.game_dir / "savegame/objlist"
    source = bytes(range(256)) + bytes(1280) + b"unparsed\x00\xff"
    _ = path.write_bytes(source)
    session = WorldLoader.load(loaded_world.state.game_dir, "fp")
    npc = session.state.npcs[255]
    npc.x, npc.y, npc.z, npc.packed_type = 0x123, 0x2AB, 5, 0xAEAB
    expected = bytearray(source)
    expected[0x3FD:0x400] = bytes.fromhex("23 ad 5a")
    expected[0x5FE:0x600] = bytes.fromhex("ab ae")

    result = WorldSaver.save(session)

    assert path.read_bytes() == bytes(expected)
    assert path.with_suffix(".bak").read_bytes() == source
    assert result.touched == (path,)
    assert result.backups == (path.with_suffix(".bak"),)


def test_save_writes_objects_npcs_chunks_map_in_order_and_roundtrips(
    loaded_world: WorldSession,
) -> None:
    item = loaded_world.editor.new_object()
    loaded_world.editor.add_object_at(item, 5, 6, 0)
    loaded_world.editor.set_map_tile(42, 3, 4, 0)
    loaded_world.editor.set_chunk(0, 8, 0, 0)

    result = WorldSaver.save(loaded_world)

    assert tuple(path.name for path in result.touched) == (
        "objblkaa",
        "objlist",
        "chunks",
        "map",
    )
    assert result.backups[0].read_bytes() == bytes(2)
    assert result.backups[2].read_bytes() == bytes(64)
    assert result.backups[3].read_bytes() == bytes(32256)
    assert not loaded_world.state.dirty_object_blocks
    assert not loaded_world.state.terrain.chunks_dirty
    assert not loaded_world.state.terrain.map_dirty
    reloaded = WorldLoader.load(loaded_world.state.game_dir, "fp")
    assert reloaded.editor.map_tile_at(3, 4, 0) == 42
    point = reloaded.editor.objects_at(5, 6, 0)
    assert point is not None
    assert point[0].packed_type == item.packed_type


def test_failed_save_preserves_pending_flags_and_cleans_temporary_files(
    loaded_world: WorldSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_world.editor.add_object_at(loaded_world.editor.new_object(), 5, 6, 0)
    loaded_world.editor.set_map_tile(42, 0, 0, 0)
    loaded_world.editor.set_chunk(0, 0, 0, 0)
    original_replace = Path.replace

    def fail_objlist_replace(path: Path, target: Path) -> Path:
        if target.name == "objlist":
            raise PermissionError(target)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_objlist_replace)

    with pytest.raises(PermissionError):
        _ = WorldSaver.save(loaded_world)

    assert not loaded_world.state.dirty_object_blocks
    assert loaded_world.state.terrain.chunks_dirty
    assert loaded_world.state.terrain.map_dirty
    assert (loaded_world.state.game_dir / "savegame/objlist").read_bytes() == bytes(
        1536
    )
    assert not tuple(loaded_world.state.game_dir.rglob("*.tmp"))


def test_save_retains_uppercase_filenames(loaded_world: WorldSession) -> None:
    root = loaded_world.state.game_dir
    _ = (root / "savegame/objlist").rename(root / "savegame/OBJLIST")
    _ = (root / "savegame").rename(root / "SAVEGAME")
    _ = (root / "chunks").rename(root / "CHUNKS")
    loaded_world.editor.set_map_tile(42, 0, 0, 0)

    result = WorldSaver.save(loaded_world)

    assert tuple(path.name for path in result.touched) == ("OBJLIST", "CHUNKS")
    assert tuple(path.name for path in result.backups) == ("OBJLIST.bak", "CHUNKS.bak")
    assert result.touched[0].parent.name == "SAVEGAME"


def test_load_resolves_relative_directory_without_changing_cwd(
    loaded_world: WorldSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(loaded_world.state.game_dir.parent)
    session = WorldLoader.load(Path("world"), "fp")
    assert session.state.game_dir == loaded_world.state.game_dir
    assert Path.cwd() == loaded_world.state.game_dir.parent


def test_loading_without_font_after_fonted_game_clears_optional_asset(
    loaded_world: WorldSession,
    tmp_path: Path,
) -> None:
    _ = (loaded_world.state.game_dir / "u6.ch").write_bytes(bytes((0x80,)) * 2048)
    first = WorldLoader.load(loaded_world.state.game_dir, "fp")
    other = tmp_path / "other"
    write_game_fixture(other, "se", "other")
    second = WorldLoader.load(other, "se")
    assert first.state.assets.font is not None
    assert first.state.assets.font.character(0, transparent=True)[0] == 0x48
    assert second.state.assets.font is None
    assert first.state.assets.catalog.name_for_tile(0) == "fixture"
    assert second.state.assets.catalog.name_for_tile(0) == "other"


def test_failed_backup_keeps_original_file_and_dirty_block(
    loaded_world: WorldSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_world.editor.add_object_at(loaded_world.editor.new_object(), 5, 6, 0)
    original_replace = Path.replace

    def fail_backup_replace(path: Path, target: Path) -> Path:
        if target.name == "objblkaa.bak":
            raise PermissionError(target)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_backup_replace)
    with pytest.raises(PermissionError):
        _ = WorldSaver.save(loaded_world)
    assert loaded_world.state.dirty_object_blocks == {0}
    assert (loaded_world.state.game_dir / "savegame/objblkaa").read_bytes() == bytes(2)
    assert not tuple(loaded_world.state.game_dir.rglob("*.tmp"))


def test_no_edit_save_preserves_raw_npc_dungeon_coordinates(
    loaded_world: WorldSession,
) -> None:
    path = loaded_world.state.game_dir / "savegame/objlist"
    source = bytearray(bytes(range(256)) + bytes(1280) + b"opaque-tail")
    source[0x100:0x103] = bytes.fromhex("23 ad 5a")
    source[0x400:0x402] = bytes.fromhex("ab ae")
    _ = path.write_bytes(source)
    session = WorldLoader.load(loaded_world.state.game_dir, "fp")

    _ = WorldSaver.save(session)

    assert path.read_bytes() == bytes(source)
    assert path.with_suffix(".bak").read_bytes() == bytes(source)
