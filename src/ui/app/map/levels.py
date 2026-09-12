"""Editor labels for numeric map slots; these names are not stored in MAP."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from game.models.game import GameType


@dataclass(frozen=True, slots=True)
class WorldLevel:
    """A named map slot that remains selectable even when unused by the game."""

    index: int
    name: str
    unused: bool = False

    @property
    def label(self) -> str:
        """Return the shared selector and minimap label."""
        return f"{self.name} (unused)" if self.unused else self.name


# Map identities and indices: https://www.reenigne.org/blog/u6maps/
# Its md0..md5 and se0..se3 image names identify the zero-based map slots.
WORLD_LEVELS: Final = MappingProxyType(
    {
        GameType.FP: (
            WorldLevel(0, "Britannia"),
            WorldLevel(1, "Dungeon level 1"),
            WorldLevel(2, "Dungeon level 2"),
            WorldLevel(3, "Dungeon level 3"),
            WorldLevel(4, "Dungeon level 4"),
            WorldLevel(5, "Gargoyle Realm"),
        ),
        GameType.MD: (
            WorldLevel(0, "Mars"),
            WorldLevel(1, "Mines"),
            WorldLevel(2, "Dreamworld 1"),
            WorldLevel(3, "Dreamworld 2"),
            WorldLevel(4, "Mine & Martian city"),
            WorldLevel(5, "Coal mine & power plant"),
        ),
        GameType.SE: (
            WorldLevel(0, "Eodon Valley"),
            WorldLevel(1, "Myrmidex caves"),
            WorldLevel(2, "Surface caves"),
            WorldLevel(3, "Kotl city"),
            WorldLevel(4, "Map 4", unused=True),
            WorldLevel(5, "Map 5", unused=True),
        ),
    },
)
