from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, assert_never

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPaintEvent, QPainter, QPainterPath, QPen, QPolygonF, QRadialGradient
from PySide6.QtWidgets import QWidget

from pu6e_qt.theme import THEME


type WorldLandmark = Literal["castle", "observatory", "jungle"]


@dataclass(frozen=True, slots=True)
class WorldScene:
    sky: str
    horizon: str
    foreground: str
    light: str
    landmark: WorldLandmark
    description: str


WORLD_SCENES: Final[dict[str, WorldScene]] = {
    "fp": WorldScene(
        THEME.britannia_sky,
        THEME.britannia_horizon,
        THEME.britannia_foreground,
        THEME.britannia_light,
        "castle",
        "Return to Britannia. Explore every tile, uncover the underworld, "
        "and shape the world that awaits the Avatar.",
    ),
    "md": WorldScene(
        THEME.mars_sky,
        THEME.mars_horizon,
        THEME.mars_foreground,
        THEME.mars_light,
        "observatory",
        "Journey across the red planet, chart lost Martian cities, "
        "and uncover an adventure beyond the stars.",
    ),
    "se": WorldScene(
        THEME.eodon_sky,
        THEME.eodon_horizon,
        THEME.eodon_foreground,
        THEME.eodon_light,
        "jungle",
        "Venture into the hidden valley of Eodon, where ancient tribes "
        "and prehistoric mysteries await.",
    ),
}


class WorldArtwork(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._scene = WORLD_SCENES["fp"]
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

    def set_world(self, game: str) -> None:
        self._scene = WORLD_SCENES[game]
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        bounds = QRectF(self.rect())
        scene = self._scene
        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            sky = QLinearGradient(0, 0, 0, bounds.height())
            sky.setColorAt(0, QColor(scene.sky))
            sky.setColorAt(0.58, QColor(scene.horizon))
            sky.setColorAt(1, QColor(scene.foreground))
            painter.fillRect(bounds, sky)

            center = QPointF(bounds.width() * 0.71, bounds.height() * 0.25)
            glow = QRadialGradient(center, bounds.height() * 0.25)
            luminous = QColor(scene.light)
            luminous.setAlpha(105)
            transparent = QColor(scene.light)
            transparent.setAlpha(0)
            glow.setColorAt(0, luminous)
            glow.setColorAt(1, transparent)
            painter.fillRect(bounds, glow)
            painter.setPen(Qt.PenStyle.NoPen)
            sun = QColor(scene.light)
            sun.setAlpha(174)
            painter.setBrush(sun)
            radius = bounds.height() * 0.09
            painter.drawEllipse(center, radius, radius)

            distant = QPolygonF([
                QPointF(bounds.width() * x, bounds.height() * y)
                for x, y in (
                    (0, 0.65), (0.12, 0.48), (0.25, 0.62), (0.39, 0.4),
                    (0.55, 0.61), (0.72, 0.36), (0.86, 0.56), (1, 0.42),
                    (1, 1), (0, 1),
                )
            ])
            painter.setBrush(QColor(scene.horizon).darker(113))
            painter.drawPolygon(distant)

            near = QPainterPath(QPointF(0, bounds.height() * 0.73))
            near.cubicTo(
                bounds.width() * 0.22, bounds.height() * 0.58,
                bounds.width() * 0.34, bounds.height() * 0.8,
                bounds.width() * 0.53, bounds.height() * 0.65,
            )
            near.cubicTo(
                bounds.width() * 0.75, bounds.height() * 0.51,
                bounds.width() * 0.9, bounds.height() * 0.77,
                bounds.width(), bounds.height() * 0.62,
            )
            near.lineTo(bounds.width(), bounds.height())
            near.lineTo(0, bounds.height())
            near.closeSubpath()
            painter.fillPath(near, QColor(scene.foreground))
            self._paint_landmark(painter, bounds)

            veil = QLinearGradient(0, 0, 0, bounds.height())
            translucent = QColor(THEME.surface_canvas)
            translucent.setAlpha(18)
            middle = QColor(THEME.surface_canvas)
            middle.setAlpha(80)
            deep = QColor(THEME.surface_canvas)
            deep.setAlpha(244)
            veil.setColorAt(0, translucent)
            veil.setColorAt(0.47, middle)
            veil.setColorAt(0.78, deep)
            veil.setColorAt(1, QColor(THEME.surface_canvas))
            painter.fillRect(bounds, veil)

    def _paint_landmark(self, painter: QPainter, bounds: QRectF) -> None:
        scene = self._scene
        width = bounds.width()
        height = bounds.height()
        ink = QColor(scene.foreground).darker(135)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(ink)

        match scene.landmark:
            case "castle":
                painter.drawRect(QRectF(width * 0.57, height * 0.48, width * 0.2, height * 0.2))
                painter.drawRect(QRectF(width * 0.59, height * 0.36, width * 0.055, height * 0.15))
                painter.drawRect(QRectF(width * 0.7, height * 0.41, width * 0.05, height * 0.11))
                tower = QPolygonF((
                    QPointF(width * 0.578, height * 0.36),
                    QPointF(width * 0.617, height * 0.29),
                    QPointF(width * 0.655, height * 0.36),
                ))
                painter.drawPolygon(tower)
                painter.fillRect(QRectF(width * 0.61, height * 0.42, 5, 11), QColor(scene.light))
                painter.fillRect(QRectF(width * 0.713, height * 0.47, 5, 9), QColor(scene.light))
            case "observatory":
                dome = QPainterPath()
                dome.moveTo(width * 0.56, height * 0.62)
                dome.arcTo(QRectF(width * 0.56, height * 0.44, width * 0.2, height * 0.22), 0, 180)
                dome.closeSubpath()
                painter.fillPath(dome, ink)
                painter.drawRect(QRectF(width * 0.55, height * 0.59, width * 0.23, height * 0.09))
                painter.setPen(QPen(QColor(scene.light), 2))
                painter.drawLine(QPointF(width * 0.66, height * 0.48), QPointF(width * 0.72, height * 0.32))
                painter.drawLine(QPointF(width * 0.67, height * 0.42), QPointF(width * 0.74, height * 0.4))
            case "jungle":
                creature = QPainterPath(QPointF(width * 0.57, height * 0.6))
                creature.cubicTo(width * 0.61, height * 0.52, width * 0.68, height * 0.52, width * 0.71, height * 0.56)
                creature.lineTo(width * 0.76, height * 0.49)
                creature.lineTo(width * 0.8, height * 0.5)
                creature.lineTo(width * 0.82, height * 0.56)
                creature.lineTo(width * 0.78, height * 0.59)
                creature.lineTo(width * 0.74, height * 0.57)
                creature.lineTo(width * 0.7, height * 0.63)
                creature.lineTo(width * 0.69, height * 0.7)
                creature.lineTo(width * 0.66, height * 0.7)
                creature.lineTo(width * 0.65, height * 0.63)
                creature.lineTo(width * 0.6, height * 0.66)
                creature.lineTo(width * 0.57, height * 0.7)
                creature.lineTo(width * 0.54, height * 0.69)
                creature.closeSubpath()
                painter.fillPath(creature, ink)
                painter.setPen(QPen(ink, 7))
                painter.drawLine(QPointF(width * 0.37, height * 0.71), QPointF(width * 0.39, height * 0.43))
                painter.setPen(QPen(ink, 4))
                painter.drawLine(QPointF(width * 0.39, height * 0.48), QPointF(width * 0.32, height * 0.52))
                painter.drawLine(QPointF(width * 0.39, height * 0.46), QPointF(width * 0.47, height * 0.5))
            case unreachable:
                assert_never(unreachable)
