from __future__ import annotations

from pu6e_qt.theme import THEME


def launcher_stylesheet() -> str:
    return f"""
        QWidget[objectName="pu6e-launcher"], QDialog[objectName="game-configurator"] {{
            background: {THEME.surface_canvas};
        }}
        QWidget[objectName="atlas-world-rail"] {{
            background: {THEME.surface_launcher_rail};
            border-right: 1px solid {THEME.border_subtle};
        }}
        QLabel[objectName="launcher-wordmark"] {{
            color: {THEME.text_primary};
            font-family: Georgia, "Noto Serif", serif;
            font-size: {THEME.launcher_brand_size}px;
            font-weight: 600;
            padding-left: {THEME.space_1}px;
        }}
        QLabel[objectName="launcher-kicker"], QLabel[objectName="launcher-worlds-label"],
        QLabel[objectName="launcher-footer"],
        QLabel[launcherRole="gameSetting"] {{
            color: {THEME.text_muted};
            font-size: {THEME.caption_size}px;
            letter-spacing: 1px;
            padding-left: {THEME.space_1}px;
        }}
        QLabel[objectName="launcher-kicker"] {{
            color: {THEME.accent_primary};
        }}
        QPushButton[launcherRole="gameCard"] {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: {THEME.control_radius}px;
            padding: 0;
            text-align: left;
        }}
        QPushButton[launcherRole="gameCard"]:hover {{
            background: {THEME.surface_panel};
            border-color: {THEME.border_subtle};
        }}
        QPushButton[launcherRole="gameCard"]:checked {{
            background: {THEME.accent_wash};
            border-color: {THEME.accent_pressed};
        }}
        QLabel[launcherRole="gameBadge"] {{
            background: {THEME.accent_wash};
            border-radius: {THEME.control_radius}px;
            color: {THEME.accent_primary};
            font-family: Georgia, "Noto Serif", serif;
            font-size: {THEME.section_size}px;
            font-weight: 600;
        }}
        QLabel[launcherRole="gameTitle"] {{
            color: {THEME.text_primary};
            font-size: {THEME.title_size}px;
            font-weight: 600;
        }}
        QLabel[launcherRole="gameRailTitle"] {{
            background: transparent;
            color: {THEME.text_primary};
            font-size: {THEME.body_size}px;
            font-weight: 550;
        }}
        QLabel[launcherRole="gameStatus"] {{
            background: transparent;
            font-size: {THEME.caption_size}px;
        }}
        QLabel[launcherRole="gameStatus"][launcherReady="true"] {{
            color: {THEME.status_success};
        }}
        QLabel[launcherRole="gameStatus"][launcherReady="false"] {{
            color: {THEME.text_muted};
        }}
        QLabel[launcherRole="gameStatus"][launcherWarning="true"] {{
            color: {THEME.status_warning};
            font-weight: 500;
        }}
        QLabel[launcherRole="worldSetting"], QLabel[launcherRole="worldOverline"] {{
            background: transparent;
            color: {THEME.accent_hover};
            font-size: {THEME.caption_size}px;
            letter-spacing: 1px;
        }}
        QLabel[launcherRole="worldTitle"] {{
            background: transparent;
            color: {THEME.text_primary};
            font-family: Georgia, "Noto Serif", serif;
            font-size: {THEME.launcher_world_size}px;
            font-weight: 600;
        }}
        QLabel[launcherRole="worldSubtitle"] {{
            background: transparent;
            color: {THEME.text_secondary};
            font-size: {THEME.launcher_subtitle_size}px;
        }}
        QLabel[launcherRole="worldDescription"] {{
            background: transparent;
            color: {THEME.text_secondary};
            font-size: {THEME.body_size}px;
        }}
        QLabel[launcherRole="worldStatus"][launcherReady="true"] {{
            background: transparent;
            color: {THEME.status_success};
        }}
        QLabel[launcherRole="worldStatus"][launcherWarning="true"] {{
            background: transparent;
            color: {THEME.status_warning};
            font-weight: 600;
        }}
        QLabel[launcherRole="worldPath"] {{
            background: transparent;
            color: {THEME.text_muted};
            font-size: {THEME.caption_size}px;
        }}
        QPushButton[launcherRole="launchButton"] {{
            background: {THEME.accent_primary};
            border-radius: {THEME.control_radius + 2}px;
            color: {THEME.surface_canvas};
            font-size: {THEME.body_size}px;
            font-weight: 600;
            min-height: {THEME.space_7}px;
            padding: {THEME.space_2}px {THEME.space_5}px;
        }}
        QPushButton[launcherRole="launchButton"]:hover {{
            background: {THEME.accent_hover};
        }}
        QPushButton[launcherRole="launchButton"]:disabled {{
            background: {THEME.surface_pressed};
            color: {THEME.text_disabled};
        }}
        QPushButton[launcherRole="secondaryButton"], QToolButton[launcherRole="stageSettings"] {{
            background: {THEME.surface_panel};
            border: 1px solid {THEME.border_default};
            border-radius: {THEME.control_radius}px;
            color: {THEME.text_secondary};
            min-height: {THEME.space_7}px;
            padding: {THEME.space_2}px {THEME.space_3}px;
        }}
        QToolButton[launcherRole="settingsButton"], QToolButton[launcherRole="warningButton"] {{
            background: transparent;
            border: 1px solid transparent;
            border-radius: {THEME.control_radius}px;
            padding: {THEME.space_1}px;
        }}
        QToolButton[launcherRole="settingsButton"]:hover,
        QToolButton[launcherRole="warningButton"]:hover {{
            background: {THEME.surface_hover};
            border-color: {THEME.border_default};
        }}
        QToolButton[launcherRole="stageWarning"] {{
            background: {THEME.surface_panel};
            border: 1px solid {THEME.status_warning};
            border-radius: {THEME.control_radius}px;
            color: {THEME.status_warning};
            font-weight: 500;
            padding: {THEME.space_2}px {THEME.space_3}px;
        }}
        QToolButton[launcherRole="stageWarning"]:hover {{
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
