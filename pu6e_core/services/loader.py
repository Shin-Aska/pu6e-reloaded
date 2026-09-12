"""Load a complete world locally before exposing its editable session."""

from typing import TYPE_CHECKING, Final

from pu6e_core.formats.assets import load_assets
from pu6e_core.formats.npcs import decode_objlist
from pu6e_core.formats.objects import decode_object_block
from pu6e_core.formats.resources import (
    OBJECT_BLOCK_FILES,
    decode_resource,
    resolve_dos_path,
)
from pu6e_core.formats.terrain import decode_chunks, decode_map
from pu6e_core.models.game import GameType
from pu6e_core.models.world import WorldMap, WorldState
from pu6e_core.services.session import WorldSession

if TYPE_CHECKING:
    from pathlib import Path

    from pu6e_core.models.objects import WorldObject

_MAX_WORLD_LEVEL: Final = 5


class WorldLoader:
    """Build independent worlds without global state or process directory changes."""

    @staticmethod
    def load(directory: Path, game: GameType | str) -> WorldSession:
        """Return a fully populated session after every required file is parsed."""
        game_type = GameType(game)
        game_dir = resolve_dos_path(directory.expanduser().resolve())
        assets = load_assets(game_dir, game_type)
        terrain = WorldMap(
            decode_map(decode_resource(game_dir, game_type, "map")),
            decode_chunks(decode_resource(game_dir, game_type, "chunks")),
        )
        inventories: list[list[WorldObject]] = [[] for _ in range(256)]
        blocks = [
            decode_object_block(
                decode_resource(game_dir, game_type, filename),
                assets.catalog,
                inventories,
            )
            for filename in OBJECT_BLOCK_FILES
        ]
        objlist = decode_resource(game_dir, game_type, "objlist")
        npcs = decode_objlist(objlist, assets.catalog, inventories)
        state = WorldState(
            game_type=game_type,
            game_dir=game_dir,
            terrain=terrain,
            object_blocks=blocks,
            npcs=npcs,
            assets=assets,
            dirty_object_blocks=set(),
            objlist_prefix=objlist[:0x100],
            objlist_trailer=objlist[0x600:],
        )
        session = WorldSession(state)
        for npc in npcs:
            if npc.packed_type and npc.z <= _MAX_WORLD_LEVEL:
                session.editor.add_object_at(npc, npc.x, npc.y, npc.z)
        session.editor.clear_changes()
        return session
