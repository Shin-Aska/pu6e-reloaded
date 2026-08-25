from __future__ import annotations

from dataclasses import dataclass

import mapedit_gl as render
from U6 import Map, U6util, obj
from pu6e_qt.controller import EditorController


@dataclass(frozen=True, slots=True)
class DragOrigin:
    x: int
    y: int
    z: int
    item: obj.Obj | None


class MapInteraction:
    def __init__(self, controller: EditorController) -> None:
        self.controller = controller
        self.drag_origin: DragOrigin | None = None
        self.right_origin: tuple[int, int, int] | None = None

    def press_left(self, x: int, y: int, z: int) -> None:
        item: obj.Obj | None = U6util.lookable_at(x, y, z) if render.display_objects else None
        self.drag_origin = DragOrigin(x=x, y=y, z=z, item=item)

    def release_left(
        self,
        x: int,
        y: int,
        z: int,
        *,
        shift: bool,
        control: bool,
    ) -> None:
        origin = self.drag_origin
        self.drag_origin = None
        if origin is not None and (origin.x, origin.y, origin.z) != (x, y, z):
            self._drop(origin, x, y, z, shift=shift, control=control)

        self.controller.set_selected_tile(Map.maptile_at(x, y, z))
        selected = U6util.lookable_at(x, y, z) if render.display_objects else None
        self.controller.select_location(x, y, z)
        self.controller.select_object(selected)

    def _drop(
        self,
        origin: DragOrigin,
        x: int,
        y: int,
        z: int,
        *,
        shift: bool,
        control: bool,
    ) -> None:
        if shift:
            source_chunk = Map.world_to_chunk_num(origin.x, origin.y, origin.z)[0]
            self.controller.set_chunk(source_chunk, x, y, z)
            return

        item = origin.item
        if item is not None:
            target_x = x + item.x - origin.x
            target_y = y + item.y - origin.y
            if control:
                self.controller.copy_object(item, target_x, target_y, z)
            else:
                self.controller.move_object(item, target_x, target_y, z)
            return

        if self.controller.terrain_mode:
            source_tile = Map.maptile_at(origin.x, origin.y, origin.z)
            if 0 <= source_tile <= 255:
                self.controller.paint_tile(source_tile, x, y, z)

    def press_right(self, x: int, y: int, z: int) -> bool:
        tile_id = self.controller.selected_tile
        if not 0 <= tile_id <= 255:
            self.right_origin = None
            return False
        self.controller.paint_tile(tile_id, x, y, z)
        self.right_origin = (x, y, z)
        return True

    def drag_right(self, x: int, y: int, z: int) -> bool:
        if self.right_origin is None or self.right_origin == (x, y, z):
            return False
        return self.press_right(x, y, z)

    def release_right(self) -> None:
        self.right_origin = None
