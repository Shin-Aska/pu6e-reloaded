from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from PySide6.QtCore import Qt


@dataclass(frozen=True, slots=True)
class NavigationAction:
    dx: int = 0
    dy: int = 0
    level_delta: int = 0
    zoom_factor: float = 1.0


_ARROWS: Final = {
    Qt.Key.Key_Left.value: (-1, 0),
    Qt.Key.Key_Right.value: (1, 0),
    Qt.Key.Key_Up.value: (0, -1),
    Qt.Key.Key_Down.value: (0, 1),
}
_KEYPAD: Final = {
    Qt.Key.Key_1.value: (-8, 8),
    Qt.Key.Key_2.value: (0, 8),
    Qt.Key.Key_3.value: (8, 8),
    Qt.Key.Key_4.value: (-8, 0),
    Qt.Key.Key_6.value: (8, 0),
    Qt.Key.Key_7.value: (-8, -8),
    Qt.Key.Key_8.value: (0, -8),
    Qt.Key.Key_9.value: (8, -8),
    Qt.Key.Key_End.value: (-8, 8),
    Qt.Key.Key_PageDown.value: (8, 8),
    Qt.Key.Key_Home.value: (-8, -8),
    Qt.Key.Key_PageUp.value: (8, -8),
}
_ZOOM: Final = {
    Qt.Key.Key_Plus.value: 2.0,
    Qt.Key.Key_Equal.value: 2.0,
    Qt.Key.Key_Minus.value: 0.5,
}


def navigation_action(key: int, *, keypad: bool) -> NavigationAction | None:
    zoom_factor = _ZOOM.get(key)
    if zoom_factor is not None:
        return NavigationAction(zoom_factor=zoom_factor)

    arrow = _ARROWS.get(key)
    if arrow is not None:
        multiplier = 8 if keypad else 1
        return NavigationAction(dx=arrow[0] * multiplier, dy=arrow[1] * multiplier)

    if not keypad:
        return None

    movement = _KEYPAD.get(key)
    if movement is not None:
        return NavigationAction(dx=movement[0], dy=movement[1])

    if key in (Qt.Key.Key_0.value, Qt.Key.Key_Insert.value):
        return NavigationAction(level_delta=-1)
    if key in (Qt.Key.Key_5.value, Qt.Key.Key_Clear.value):
        return NavigationAction(level_delta=1)
    return None
