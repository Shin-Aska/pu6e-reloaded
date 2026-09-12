"""World queries and edits bound to one explicit state instance."""

from typing import TYPE_CHECKING, override

from pu6e_core.models.coordinates import world_to_block, world_to_chunk, wrap_coords
from pu6e_core.models.objects import ObjectPoint, WorldObject

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pu6e_core.models.world import WorldState


class EditValueError(ValueError):
    """An editor input exceeds the corresponding on-disk field's range."""

    def __init__(self, field: str, value: int, maximum: int) -> None:
        self.field: str = field
        self.value: int = value
        self.maximum: int = maximum
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        return f"{self.field} must be in 0..{self.maximum}, received {self.value}"


class WorldEditor:
    """Apply edits and dirty tracking only to the world supplied at construction."""

    def __init__(self, state: WorldState) -> None:
        self.state: WorldState = state

    def objects_at(self, x: int, y: int, z: int) -> ObjectPoint | None:
        """Find a stack at its stored coordinates without creating model state."""
        for row_y, row in self.state.object_blocks[world_to_block(x, y, z)]:
            if row_y < y:
                break
            if row_y == y:
                for point_x, point in row:
                    if point_x < x:
                        break
                    if point_x == x:
                        return point
        return None

    def point_at(self, x: int, y: int, z: int) -> ObjectPoint:
        """Find or create a stack, retaining raw coordinates and descending order."""
        block = self.state.object_blocks[world_to_block(x, y, z)]
        point = ObjectPoint(x, y, z)
        for row_index, (row_y, row) in enumerate(block):
            if row_y < y:
                block.insert(row_index, (y, [(x, point)]))
                return point
            if row_y == y:
                for point_index, (point_x, current) in enumerate(row):
                    if point_x < x:
                        row.insert(point_index, (x, point))
                        return point
                    if point_x == x:
                        return current
                row.append((x, point))
                return point
        block.append((y, [(x, point)]))
        return point

    def mark_object_changed(self, x: int, y: int, z: int) -> None:
        """Mark the owning object block for persistence."""
        self.state.dirty_object_blocks.add(world_to_block(x, y, z))

    def add_object_at(self, item: WorldObject, x: int, y: int, z: int) -> None:
        """Place an object and mark its destination block as edited."""
        self.point_at(x, y, z).append(item)
        self.mark_object_changed(x, y, z)

    def remove_object(self, item: WorldObject, x: int, y: int, z: int) -> bool:
        """Remove by identity, leaving unrelated equivalent objects untouched."""
        point = self.objects_at(x, y, z)
        if point is not None:
            for index, current in enumerate(point):
                if current is item:
                    del point[index]
                    self.mark_object_changed(x, y, z)
                    return True
        return False

    def move_object(self, item: WorldObject, x: int, y: int, z: int) -> bool:
        """Move an object only if it belongs to this world's source stack."""
        if not self.remove_object(item, item.x, item.y, item.z):
            return False
        self.add_object_at(item, x, y, z)
        return True

    def copy_object(self, item: WorldObject, x: int, y: int, z: int) -> WorldObject | None:
        """Clone an ordinary object into a destination stack; NPCs cannot be copied."""
        cloned = item.clone()
        if cloned is not None:
            self.add_object_at(cloned, x, y, z)
        return cloned

    def new_object(self) -> WorldObject:
        """Create the editor's default leather helm using this world's catalog."""
        return WorldObject(self.state.assets.catalog, packed_type=1)

    def chunk_at(self, x: int, y: int, z: int) -> tuple[int, int, int]:
        """Return the terrain chunk reference and local tile offsets."""
        x, y, z = wrap_coords(x, y, z)
        scx, scy, cx, cy, tx, ty = world_to_chunk(x, y, z)
        width = 16 if z == 0 else 32
        chunk = self.state.terrain.superchunks[scx + scy * 8][cx + cy * width]
        return chunk, tx, ty

    def map_tile_at(self, x: int, y: int, z: int) -> int:
        """Read the indexed background tile at a wrapped world coordinate."""
        chunk, tx, ty = self.chunk_at(x, y, z)
        return self.state.terrain.chunks[chunk][tx + ty * 8]

    def set_map_tile(self, tile: int, x: int, y: int, z: int) -> None:
        """Edit the shared chunk tile and mark terrain chunk data dirty."""
        if not 0 <= tile <= 255:
            raise EditValueError("background tile", tile, 255)
        chunk, tx, ty = self.chunk_at(x, y, z)
        self.state.terrain.chunks[chunk][tx + ty * 8] = tile
        self.state.terrain.chunks_dirty = True

    def set_chunk(self, chunk: int, x: int, y: int, z: int) -> None:
        """Replace a twelve-bit map reference and mark the map dirty."""
        if not 0 <= chunk <= 0xFFF:
            raise EditValueError("chunk", chunk, 0xFFF)
        x, y, z = wrap_coords(x, y, z)
        scx, scy, cx, cy, _, _ = world_to_chunk(x, y, z)
        width = 16 if z == 0 else 32
        self.state.terrain.superchunks[scx + scy * 8][cx + cy * width] = chunk
        self.state.terrain.map_dirty = True

    def clear_changes(self) -> None:
        """Clear this world's object and terrain dirty markers."""
        self.state.dirty_object_blocks.clear()
        self.state.terrain.map_dirty = False
        self.state.terrain.chunks_dirty = False

    def lookable_at(self, x: int, y: int, z: int) -> WorldObject | None:
        """Find the visible object, including adjacent parts of large sprites."""
        point = self.objects_at(x, y, z)
        top = point[-1] if point else None
        if top is not None and not self.state.assets.catalog.lowest_look(top.tile):
            return top
        for dx, dy in ((1, 0), (0, 1), (1, 1)):
            for item, _ in self._adjacent(x, y, z, dx, dy):
                return item
        return top

    def is_blocked(self, x: int, y: int, z: int) -> bool:
        """Combine terrain, blocking objects, bridges, and adjacent sprite parts."""
        catalog = self.state.assets.catalog
        terrain_blocked = catalog.is_blocked(self.map_tile_at(x, y, z))
        point = self.objects_at(x, y, z)
        if point is not None:
            for item in point:
                if catalog.is_blocked(item.tile):
                    return True
                if catalog.force_passable(item.tile):
                    terrain_blocked = False
        if terrain_blocked:
            return True
        return any(
            catalog.is_blocked(tile)
            for dx, dy in ((1, 0), (0, 1), (1, 1))
            for _, tile in self._adjacent(x, y, z, dx, dy)
        )

    def _adjacent(
        self,
        x: int,
        y: int,
        z: int,
        dx: int,
        dy: int,
    ) -> Iterator[tuple[WorldObject, int]]:
        point = self.objects_at(*wrap_coords(x + dx, y + dy, z))
        if point is not None:
            size = (dx << 1) | dy
            for item in reversed(point):
                if self.state.assets.catalog.size(item.tile) & size == size:
                    yield item, item.tile - dx - dy - dx * dy
