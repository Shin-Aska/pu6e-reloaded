"""Per-world mutable data with independent edit tracking."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from game.models.assets import WorldAssets
    from game.models.game import GameType
    from game.models.objects import Npc, ObjectBlock


@dataclass(eq=False, slots=True)  # noqa: MUTABLE_OK
class WorldMap:
    """Terrain buffers are mutable so editors can change tiles and chunk references."""

    superchunks: list[list[int]]
    chunks: list[bytearray]
    map_dirty: bool = False
    chunks_dirty: bool = False


@dataclass(eq=False, slots=True)  # noqa: MUTABLE_OK
class WorldState:
    """One independently editable world and the assets defining its objects."""

    game_type: GameType
    game_dir: Path
    terrain: WorldMap
    object_blocks: list[ObjectBlock]
    npcs: list[Npc]
    assets: WorldAssets
    dirty_object_blocks: set[int] = field(default_factory=set)
    objlist_prefix: bytes = bytes(0x100)
    objlist_trailer: bytes = b""
