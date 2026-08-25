from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QToolButton, QWidget

from pu6e_qt.theme import THEME


def icon_button(label: str, parent: QWidget | None = None) -> QToolButton:
    button = QToolButton(parent)
    button.setText("")
    button.setAccessibleName(label)
    button.setToolTip(label)
    button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    button.setMinimumSize(THEME.space_6, THEME.space_6)
    return button


def section_header(title: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(title, parent)
    font = QFont(THEME.primary_font, THEME.section_size)
    font.setWeight(QFont.Weight.DemiBold)
    label.setFont(font)
    label.setAccessibleName(title)
    label.setProperty("workbenchRole", "sectionHeader")
    return label


def technical_label(value: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(value, parent)
    label.setAccessibleName(value)
    label.setProperty("workbenchRole", "technical")
    return label
