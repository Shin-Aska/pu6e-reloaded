from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QWidget,
)

from pu6e_qt.widgets import HexSpinBox


class GoToDialog(QDialog):
    def __init__(
        self,
        current_position: tuple[int, int, int],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Go to location")
        self.x = HexSpinBox(0x3FF, self)
        self.y = HexSpinBox(0x3FF, self)
        self.z = HexSpinBox(5, self)
        self.x.setValue(current_position[0])
        self.y.setValue(current_position[1])
        self.z.setValue(current_position[2])
        self.x.setAccessibleName("X coordinate in hexadecimal")
        self.y.setAccessibleName("Y coordinate in hexadecimal")
        self.z.setAccessibleName("Level in hexadecimal")

        layout = QFormLayout(self)
        layout.addRow("&X", self.x)
        layout.addRow("&Y", self.y)
        layout.addRow("&Level", self.z)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)

    def values(self) -> tuple[int, int, int]:
        return self.x.value(), self.y.value(), self.z.value()

    def accept(self) -> None:
        if self.x.hasAcceptableInput() and self.y.hasAcceptableInput() and self.z.hasAcceptableInput():
            super().accept()
