from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QLineEdit

from pu6e_qt.primitives import icon_button, section_header
from pu6e_qt.theme import THEME, apply_theme


def application() -> QApplication:
    existing = QApplication.instance()
    if existing is None:
        return QApplication([])
    return existing


def test_theme_exposes_layered_palette_and_visible_focus() -> None:
    app = application()
    apply_theme(app)

    palette = app.palette()
    assert app.style().metaObject().className() == "QStyleSheetStyle"
    assert palette.color(QPalette.ColorRole.Window).name() == THEME.surface_canvas
    assert palette.color(QPalette.ColorRole.Base).name() == THEME.surface_elevated
    assert palette.color(QPalette.ColorRole.AlternateBase).name() == THEME.surface_panel
    assert palette.color(QPalette.ColorRole.Highlight).name() == THEME.accent_wash
    assert f"border: 1px solid {THEME.accent_primary}" in app.styleSheet()

    field = QLineEdit()
    field.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    assert field.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_disabled_and_icon_only_primitives_remain_accessible() -> None:
    app = application()
    apply_theme(app)

    assert (
        app.palette()
        .color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText)
        .name()
        == THEME.text_disabled
    )
    button = icon_button("Zoom in")
    assert button.text() == ""
    assert button.accessibleName() == "Zoom in"
    assert button.toolTip() == "Zoom in"
    assert button.focusPolicy() == Qt.FocusPolicy.StrongFocus

    header = section_header("Selected object")
    assert header.accessibleName() == "Selected object"
