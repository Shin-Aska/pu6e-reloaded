from __future__ import annotations

from PySide6.QtGui import QValidator
from PySide6.QtWidgets import QSpinBox, QWidget


class HexSpinBox(QSpinBox):
    def __init__(
        self,
        maximum: int,
        parent: QWidget | None = None,
        minimum: int = 0,
    ) -> None:
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setDisplayIntegerBase(16)
        self.setAccelerated(True)
        self.setAccessibleName("Hexadecimal value")

    def textFromValue(self, value: int) -> str:
        return format(value, "x")

    def valueFromText(self, text: str) -> int:
        return int(text, 16)

    def validate(self, text: str, position: int) -> tuple[QValidator.State, str, int]:
        if not text:
            return QValidator.State.Intermediate, text, position
        try:
            value = int(text, 16)
        except ValueError:
            return QValidator.State.Invalid, text, position
        if self.minimum() <= value <= self.maximum():
            return QValidator.State.Acceptable, text.lower(), position
        return QValidator.State.Invalid, text, position
