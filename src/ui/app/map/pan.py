from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF


@dataclass(frozen=True, slots=True)
class PanAnchor:
    pointer: QPointF
    center: tuple[int, int, int]


def dragged_world_position(
    anchor: PanAnchor,
    pointer: QPointF,
    pixels_per_tile: float,
) -> tuple[int, int, int]:
    x, y, z = anchor.center
    offset = anchor.pointer - pointer
    return x + int(offset.x() / pixels_per_tile), y + int(offset.y() / pixels_per_tile), z
