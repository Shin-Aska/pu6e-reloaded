from dataclasses import dataclass
from typing import Final

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True, slots=True)
class ThemeTokens:
    surface_canvas: str = "#101215"
    surface_panel: str = "#171a1f"
    surface_elevated: str = "#1e2228"
    surface_hover: str = "#272c34"
    surface_pressed: str = "#303640"
    surface_launcher_rail: str = "#0d1116"
    text_primary: str = "#edf0f2"
    text_secondary: str = "#b6bec8"
    text_muted: str = "#818b98"
    text_disabled: str = "#626b76"
    border_default: str = "#303640"
    border_subtle: str = "#242931"
    accent_primary: str = "#d6a657"
    accent_hover: str = "#e7bb70"
    accent_pressed: str = "#b88943"
    accent_wash: str = "#332a1c"
    status_success: str = "#75b887"
    status_warning: str = "#e0b35f"
    status_error: str = "#df7771"
    britannia_sky: str = "#435d60"
    britannia_horizon: str = "#293d3e"
    britannia_foreground: str = "#131e20"
    britannia_light: str = "#dccca2"
    mars_sky: str = "#a75c3e"
    mars_horizon: str = "#653a35"
    mars_foreground: str = "#24181b"
    mars_light: str = "#efbd86"
    eodon_sky: str = "#758a64"
    eodon_horizon: str = "#405940"
    eodon_foreground: str = "#162119"
    eodon_light: str = "#e0cf8f"
    title_size: int = 18
    section_size: int = 14
    body_size: int = 13
    caption_size: int = 11
    launcher_brand_size: int = 26
    launcher_world_size: int = 42
    launcher_subtitle_size: int = 16
    space_1: int = 4
    space_2: int = 8
    space_3: int = 12
    space_4: int = 16
    space_5: int = 20
    space_6: int = 24
    space_7: int = 32
    space_8: int = 40
    launcher_rail_width: int = 232
    control_radius: int = 4
    panel_radius: int = 6
    primary_font: str = "IBM Plex Sans"
    technical_font: str = "IBM Plex Mono"


THEME: Final = ThemeTokens()


def _palette(tokens: ThemeTokens) -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(tokens.surface_canvas))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(tokens.text_primary))
    palette.setColor(QPalette.ColorRole.Base, QColor(tokens.surface_elevated))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(tokens.surface_panel))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(tokens.surface_elevated))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(tokens.text_primary))
    palette.setColor(QPalette.ColorRole.Text, QColor(tokens.text_secondary))
    palette.setColor(QPalette.ColorRole.Button, QColor(tokens.surface_panel))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(tokens.text_primary))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(tokens.text_primary))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(tokens.accent_wash))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(tokens.text_primary))
    palette.setColor(QPalette.ColorRole.Link, QColor(tokens.accent_primary))
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(tokens.text_disabled),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(tokens.text_disabled),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(tokens.text_disabled),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.HighlightedText,
        QColor(tokens.text_disabled),
    )
    return palette


def _stylesheet(tokens: ThemeTokens) -> str:
    return f"""
        * {{
            color: {tokens.text_secondary};
            font-family: "IBM Plex Sans", "Noto Sans", "Ubuntu", sans-serif;
            font-size: {tokens.body_size}px;
        }}
        QToolTip {{
            background-color: {tokens.surface_elevated};
            color: {tokens.text_primary};
            border: 1px solid {tokens.border_default};
            padding: {tokens.space_2}px;
        }}
        QMainWindow {{ background: {tokens.surface_canvas}; }}
        QDockWidget {{ color: {tokens.text_primary}; }}
        QDockWidget::title {{
            background: {tokens.surface_panel};
            border-bottom: 1px solid {tokens.border_subtle};
            padding: {tokens.space_2}px {tokens.space_3}px;
        }}
        QMenuBar, QToolBar, QStatusBar {{
            background: {tokens.surface_panel};
            border-color: {tokens.border_subtle};
        }}
        QMenuBar::item, QMenu::item, QToolButton, QPushButton {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: {tokens.control_radius}px;
            padding: {tokens.space_1}px {tokens.space_2}px;
        }}
        QMenu {{
            background: {tokens.surface_elevated};
            border: 1px solid {tokens.border_subtle};
            padding: {tokens.space_1}px;
        }}
        QMenu::separator {{ height: 1px; background: {tokens.border_subtle}; }}
        QMenuBar::item:selected, QMenu::item:selected,
        QToolButton:hover, QPushButton:hover {{
            background: {tokens.surface_hover};
            color: {tokens.text_primary};
        }}
        QToolButton:pressed, QPushButton:pressed {{ background: {tokens.surface_pressed}; }}
        QToolButton:checked, QPushButton:checked {{
            background: {tokens.accent_wash};
            border-color: {tokens.accent_primary};
            color: {tokens.text_primary};
        }}
        QTreeWidget, QListWidget, QTableView, QTextEdit, QPlainTextEdit,
        QLineEdit, QComboBox, QAbstractSpinBox {{
            background: {tokens.surface_elevated};
            border: 1px solid {tokens.border_default};
            border-radius: {tokens.control_radius}px;
            padding: {tokens.space_1}px {tokens.space_2}px;
            selection-background-color: {tokens.accent_wash};
            selection-color: {tokens.text_primary};
        }}
        QTreeWidget::item, QListWidget::item, QTableView::item {{
            padding: {tokens.space_1}px;
            border-radius: {tokens.control_radius}px;
        }}
        QTreeWidget::item:hover, QListWidget::item:hover, QTableView::item:hover {{
            background: {tokens.surface_hover};
        }}
        QTreeWidget::item:selected, QListWidget::item:selected,
        QTableView::item:selected {{ background: {tokens.accent_wash}; }}
        QTabWidget::pane {{ border-top: 1px solid {tokens.border_subtle}; }}
        QTabBar::tab {{
            background: {tokens.surface_panel};
            border: 1px solid {tokens.border_subtle};
            border-bottom: 0;
            border-top-left-radius: {tokens.control_radius}px;
            border-top-right-radius: {tokens.control_radius}px;
            padding: {tokens.space_2}px {tokens.space_3}px;
        }}
        QTabBar::tab:hover {{ background: {tokens.surface_hover}; }}
        QTabBar::tab:selected {{
            background: {tokens.surface_elevated};
            border-top-color: {tokens.accent_primary};
            color: {tokens.text_primary};
        }}
        QSplitter::handle {{ background: {tokens.border_subtle}; }}
        QSplitter::handle:hover {{ background: {tokens.accent_primary}; }}
        QScrollBar:vertical {{
            background: {tokens.surface_panel};
            width: {tokens.space_2}px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {tokens.border_default};
            border-radius: {tokens.control_radius}px;
            min-height: {tokens.space_6}px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {tokens.accent_primary}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        *:focus {{ border: 1px solid {tokens.accent_primary}; }}
        *:disabled {{ color: {tokens.text_disabled}; }}
        QLabel[workbenchRole="sectionHeader"] {{
            color: {tokens.text_primary};
            font-size: {tokens.section_size}px;
            font-weight: 600;
            padding: {tokens.space_2}px 0 {tokens.space_1}px 0;
        }}
        QLabel[workbenchRole="technical"] {{
            font-family: "IBM Plex Mono", "JetBrains Mono", "DejaVu Sans Mono", monospace;
            font-weight: 500;
        }}"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    font = QFont(THEME.primary_font, THEME.body_size)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    app.setPalette(_palette(THEME))
    app.setStyleSheet(_stylesheet(THEME))
