"""Mutable identity-based objects and their owned inventory lists."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from operator import index as integer_index
from typing import TYPE_CHECKING, Self, SupportsIndex, assert_never, overload, override

if TYPE_CHECKING:
    from game.models.assets import ObjectCatalog


class ContainmentError(ValueError):
    """An attempted inventory relationship that the world cannot represent."""

    def __init__(self, reason: str) -> None:
        self.reason: str = reason
        super().__init__(reason)

    @override
    def __str__(self) -> str:
        return self.reason


@dataclass(eq=False, slots=True)  # noqa: MUTABLE_OK
class WorldObject:
    """Editable object whose identity remains stable during placement and edits."""

    catalog: ObjectCatalog
    x: int = 0
    y: int = 0
    z: int = 0
    status: int = 0
    packed_type: int = 0
    quantity: int = 0
    quality: int = 0
    contains: list[WorldObject] = field(default_factory=list)

    @property
    def tile(self) -> int:
        """Resolve the displayed tile from the sole packed type value."""
        return self.catalog.tile_for_type(self.packed_type)

    @property
    def base_type(self) -> int:
        """Return the base object type without the frame bits."""
        return self.packed_type & 0x3FF

    def frame(self) -> int:
        """Return the frame encoded above the ten base-type bits."""
        return self.packed_type >> 10

    def set_frame(self, frame: int) -> None:
        """Change the frame while retaining the base type."""
        self.packed_type = self.base_type | (frame << 10)

    def set_type(self, packed_type: int) -> None:
        """Replace the packed type; a base-only value resets the frame to zero."""
        self.packed_type = packed_type

    def num_frames(self) -> int:
        """Count the frames before the next base type or the final VGA tile."""
        next_type = self.base_type + 1
        end = (
            self.catalog.base_tiles[next_type] if next_type < len(self.catalog.base_tiles) else 2048
        )
        return end - self.catalog.base_tiles[self.base_type]

    def in_container(self) -> bool:
        """Identify ordinary containment rather than direct NPC inventory."""
        return self.status & 0x18 == 0x08

    def in_inventory(self) -> bool:
        """Include both readied and carried direct NPC inventory items."""
        return bool(self.status & 0x10)

    def is_readied(self) -> bool:
        """Return the legacy overloaded ownership-bit predicate."""
        return bool(self.status & 0x18)

    def is_npc(self) -> bool:
        """Identify NPC slots when traversing mixed world object stacks."""
        return False

    def is_containable(self) -> bool:
        """Report whether the object may be inserted into an inventory."""
        return True

    def qty(self) -> int:
        """Treat quantity as a count only for names with a plural form."""
        name = self.catalog.name_for_tile(self.tile)
        return self.quantity if name is not None and "\\" in name else 0

    def weight(self) -> int:
        """Return one object's weight in tenths of a stone."""
        return self.catalog.weight(self.base_type)

    def weight_total(self) -> int:
        """Include contents, quantities, and the reagent and coin weight adjustment."""
        own_weight = self.weight() * max(1, self.qty())
        if 0x41 <= self.packed_type <= 0x48 or self.packed_type == 0x58:
            own_weight //= 10
        return own_weight + sum(item.weight_total() for item in self.contains)

    def name(self) -> str:
        """Expand the catalog's singular and plural notation with the proper article."""
        name = self.catalog.name_for_tile(self.tile)
        if not name:
            return "nothing"
        quantity = self.qty()
        if quantity <= 1:
            name = re.sub(r"\\[A-Za-z]*", "", name).replace("/", "")
            article = str(quantity) if quantity == 1 else self.catalog.article(self.tile)
            return f"{article} {name}" if article else name
        name = re.sub(r"/[A-Za-z]*", "", name).replace("\\", "")
        return f"{quantity} {name}"

    def insert(self, index: int, item: WorldObject) -> None:
        """Insert a child while rejecting NPC containment and ancestor cycles."""
        if not item.is_containable():
            raise ContainmentError("NPCs cannot be placed in containers")
        pending = [item]
        visited: set[int] = set()
        while pending:
            child = pending.pop()
            if child is self:
                raise ContainmentError("an object cannot contain itself or an ancestor")
            if id(child) not in visited:
                visited.add(id(child))
                pending.extend(child.contains)
        item.y = 0
        item.status |= 0x08
        self.contains.insert(index, item)

    def clone(self) -> WorldObject | None:
        """Copy mutable contents recursively while sharing the immutable catalog."""
        children: list[WorldObject] = []
        for item in self.contains:
            child = item.clone()
            if child is None:
                raise ContainmentError("NPCs cannot be cloned inside containers")
            children.append(child)
        return WorldObject(
            self.catalog,
            self.x,
            self.y,
            self.z,
            self.status,
            self.packed_type,
            self.quantity,
            self.quality,
            children,
        )

    def __iter__(self) -> Iterator[WorldObject]:
        return iter(self.contains)

    def __len__(self) -> int:
        return len(self.contains)

    def __bool__(self) -> bool:
        return True

    @overload
    def __getitem__(self, key: int) -> WorldObject: ...

    @overload
    def __getitem__(self, key: slice) -> list[WorldObject]: ...

    def __getitem__(self, key: int | slice) -> WorldObject | list[WorldObject]:
        match key:
            case int():
                return self.contains[key]
            case slice():
                return self.contains[key]
            case _:
                assert_never(key)

    def __delitem__(self, key: int | slice) -> None:
        del self.contains[key]


@dataclass(eq=False, slots=True)  # noqa: MUTABLE_OK
class Npc(WorldObject):
    """Editable NPC slot with an inventory belonging to its world instance."""

    npc_id: int = 0

    @override
    def is_npc(self) -> bool:
        return True

    @override
    def is_containable(self) -> bool:
        return False

    @override
    def clone(self) -> None:
        return None

    @override
    def weight(self) -> int:
        return 0

    @override
    def weight_total(self) -> int:
        return 0

    @override
    def insert(self, index: int, item: WorldObject) -> None:
        WorldObject.insert(self, index, item)
        item.status = (item.status | 0x10) & ~0x08


class PointAssignmentError(TypeError):
    """An integer stack index was assigned a sequence rather than an object."""

    def __init__(self, index: int) -> None:
        self.index: int = index
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        return f"point index {self.index} requires a WorldObject"


class ObjectPoint(list[WorldObject]):
    """Mutable object stack; insertion places each child at this point."""

    x: int
    y: int
    z: int

    def __init__(self, x: int, y: int, z: int) -> None:
        super().__init__()
        self.x, self.y, self.z = x, y, z

    @property
    def coords(self) -> tuple[int, int, int]:
        """Return the coordinates applied to all inserted objects."""
        return self.x, self.y, self.z

    @overload
    def __setitem__(self, index: SupportsIndex, value: WorldObject, /) -> None: ...

    @overload
    def __setitem__(
        self, index: slice[SupportsIndex | None], value: Iterable[WorldObject], /
    ) -> None: ...

    @override
    def __setitem__(
        self,
        index: SupportsIndex | slice[SupportsIndex | None],
        value: WorldObject | Iterable[WorldObject],
        /,
    ) -> None:
        match index:
            case SupportsIndex():
                match value:
                    case WorldObject():
                        self._place(value)
                        super().__setitem__(index, value)
                    case Iterable():
                        raise PointAssignmentError(integer_index(index))
                    case _:
                        assert_never(value)
            case slice():
                items = list(value)
                for item in items:
                    self._place(item)
                super().__setitem__(index, items)
            case _:
                assert_never(index)

    @override
    def append(self, value: WorldObject) -> None:
        self._place(value)
        super().append(value)

    @override
    def insert(self, index: SupportsIndex, value: WorldObject) -> None:
        self._place(value)
        super().insert(index, value)

    @override
    def extend(self, values: Iterable[WorldObject]) -> None:
        for value in list(values):
            self.append(value)

    @override
    def __iadd__(self, values: Iterable[WorldObject]) -> Self:
        self.extend(values)
        return self

    def _place(self, item: WorldObject) -> None:
        item.x, item.y, item.z = self.coords
        item.status &= ~0x18


type ObjectRow = list[tuple[int, ObjectPoint]]
type ObjectBlock = list[tuple[int, ObjectRow]]

__all__ = ["ContainmentError", "Npc", "ObjectBlock", "ObjectPoint", "ObjectRow", "WorldObject"]
