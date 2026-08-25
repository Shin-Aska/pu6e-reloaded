from __future__ import annotations

from typing import Final

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from pu6e_qt.theme import THEME


_PATHS: Final[dict[str, str]] = {
    "save": '<path d="M5 4h12l3 3v13H4V5a1 1 0 0 1 1-1z"/><path d="M8 4v6h8V4M8 20v-7h8v7"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-2"/>',
    "redo": '<path d="m15 14 5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h2"/>',
    "locate": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/>',
    "zoom-out": '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5M7 10h6"/>',
    "zoom-in": '<circle cx="10" cy="10" r="6"/><path d="m15 15 5 5M7 10h6m-3-3v6"/>',
    "actual-size": '<path d="M8 4H4v4m12-4h4v4M4 16v4h4m8 0h4v-4"/><path d="M9 9v6m6-6v6"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5z"/><path d="m3 12 9 5 9-5m-18 4 9 5 9-5"/>',
    "ascend": '<path d="m6 15 6-6 6 6"/>',
    "descend": '<path d="m6 9 6 6 6-6"/>',
    "grid": '<rect x="4" y="4" width="16" height="16" rx="1"/><path d="M4 12h16M12 4v16"/>',
    "objects": '<rect x="4" y="6" width="9" height="9" rx="1"/><rect x="11" y="9" width="9" height="9" rx="1"/>',
    "terrain": '<path d="m4 20 4.5-1L19 8l-3-3L5 16l-1 4z"/><path d="m13.5 7.5 3 3"/>',
    "quests": '<path d="M5 4h12a2 2 0 0 1 2 2v14H7a2 2 0 0 1-2-2V4z"/><path d="M5 17h14M9 8h6m-6 4h4"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2m0 14v2M3 12h2m14 0h2m-3.6-6.4-1.4 1.4M7 17l-1.4 1.4m12.8 0L17 17M7 7 5.6 5.6"/><circle cx="12" cy="12" r="7"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3V7z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/>',
}


def action_icon(name: str) -> QIcon:
    icon = QIcon()
    for mode, color in (
        (QIcon.Mode.Normal, THEME.text_secondary),
        (QIcon.Mode.Active, THEME.text_primary),
        (QIcon.Mode.Disabled, THEME.text_disabled),
        (QIcon.Mode.Selected, THEME.accent_primary),
    ):
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        pixmap = QPixmap(20, 20)
        pixmap.fill(QColor(Qt.GlobalColor.transparent))
        with QPainter(pixmap) as painter:
            renderer.render(painter)
        icon.addPixmap(pixmap, mode)
    return icon
