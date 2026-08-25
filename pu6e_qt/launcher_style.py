from __future__ import annotations

from pu6e_qt.theme import THEME


def launcher_stylesheet() -> str:
    return f"""
        QWidget[objectName="pu6e-launcher"], QDialog[objectName="game-configurator"] {{
            background: {THEME.surface_canvas};
        }}
        QLabel[objectName="launcher-wordmark"] {{
            color: {THEME.text_primary};
            font-size: 32px;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        QLabel[objectName="launcher-kicker"], QLabel[objectName="launcher-footer"],
        QLabel[launcherRole="gameSetting"] {{
            color: {THEME.text_muted};
            font-size: {THEME.caption_size}px;
            letter-spacing: 1px;
        }}
        QLabel[objectName="launcher-description"] {{
            color: {THEME.text_secondary};
            font-size: {THEME.section_size}px;
        }}
        QFrame[launcherRole="gameCard"] {{
            background: {THEME.surface_panel};
            border: 1px solid {THEME.border_subtle};
            border-radius: {THEME.panel_radius + THEME.space_1}px;
        }}
        QFrame[launcherRole="gameCard"][launcherReady="true"] {{
            border-color: {THEME.border_default};
        }}
        QLabel[launcherRole="gameBadge"] {{
            background: {THEME.accent_wash};
            border-radius: {THEME.panel_radius}px;
            color: {THEME.accent_primary};
            font-size: {THEME.title_size}px;
            font-weight: 700;
        }}
        QLabel[launcherRole="gameTitle"] {{
            color: {THEME.text_primary};
            font-size: {THEME.title_size}px;
            font-weight: 600;
        }}
        QLabel[launcherRole="gameSubtitle"] {{
            color: {THEME.text_secondary};
        }}
        QLabel[launcherRole="gameStatus"][launcherReady="true"] {{
            color: {THEME.status_success};
        }}
        QLabel[launcherRole="gameStatus"][launcherReady="false"] {{
            color: {THEME.text_muted};
        }}
        QLabel[launcherRole="gameStatus"][launcherWarning="true"] {{
            color: {THEME.status_warning};
            font-weight: 600;
        }}
        QLabel[launcherRole="gamePath"] {{
            color: {THEME.text_muted};
            font-size: {THEME.caption_size}px;
        }}
        QPushButton[launcherRole="launchButton"] {{
            background: {THEME.accent_primary};
            border-radius: {THEME.control_radius + 2}px;
            color: {THEME.surface_canvas};
            font-size: {THEME.body_size}px;
            font-weight: 600;
            min-height: 30px;
            padding: {THEME.space_2}px {THEME.space_4}px;
        }}
        QPushButton[launcherRole="launchButton"]:hover {{
            background: {THEME.accent_hover};
        }}
        QPushButton[launcherRole="launchButton"]:disabled {{
            background: {THEME.surface_pressed};
            color: {THEME.text_disabled};
        }}
        QToolButton[launcherRole="settingsButton"] {{
            border: 1px solid {THEME.border_default};
            border-radius: {THEME.panel_radius}px;
            padding: {THEME.space_2}px;
        }}
        QToolButton[launcherRole="warningButton"] {{
            background: {THEME.accent_wash};
            border: 1px solid {THEME.status_warning};
            border-radius: {THEME.panel_radius}px;
            color: {THEME.status_warning};
            font-weight: 600;
            padding: {THEME.space_2}px {THEME.space_3}px;
        }}
        QToolButton[launcherRole="warningButton"]:hover {{
            background: {THEME.surface_hover};
            color: {THEME.text_primary};
        }}
        QLabel[objectName="configuration-status"] {{
            background: {THEME.surface_panel};
            border: 1px solid {THEME.border_subtle};
            border-radius: {THEME.panel_radius}px;
            padding: {THEME.space_3}px;
        }}
        QLabel[objectName="configuration-guidance"] {{
            color: {THEME.text_muted};
        }}
    """
