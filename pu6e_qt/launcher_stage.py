from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QToolButton, QVBoxLayout, QWidget

from pu6e_qt.game_profiles import GameProfile
from pu6e_qt.icons import action_icon
from pu6e_qt.launcher_art import WORLD_SCENES, WorldArtwork
from pu6e_qt.launcher_cards import explanation_for_issue, status_for_issue
from pu6e_qt.theme import THEME


class WorldStage(WorldArtwork):
    launch_requested = Signal(str)
    configure_requested = Signal(str)

    def __init__(self, profile: GameProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = profile.specification.key
        self.setObjectName("atlas-world-stage")

        self.setting_label = QLabel(self)
        self.setting_label.setProperty("launcherRole", "worldSetting")

        self.settings_button = QToolButton(self)
        self.settings_button.setIcon(action_icon("settings"))
        self.settings_button.setProperty("launcherRole", "stageSettings")
        self.settings_button.clicked.connect(lambda: self.configure_requested.emit(self.game))

        header = QHBoxLayout()
        header.addWidget(self.setting_label)
        header.addStretch()
        header.addWidget(self.settings_button)

        overline = QLabel("WORLDS OF ADVENTURE", self)
        overline.setProperty("launcherRole", "worldOverline")

        self.title_label = QLabel(self)
        self.title_label.setProperty("launcherRole", "worldTitle")
        self.title_label.setWordWrap(True)

        self.subtitle_label = QLabel(self)
        self.subtitle_label.setProperty("launcherRole", "worldSubtitle")

        self.description_label = QLabel(self)
        self.description_label.setProperty("launcherRole", "worldDescription")
        self.description_label.setWordWrap(True)
        self.description_label.setMaximumWidth(THEME.launcher_rail_width * 2)

        self.launch_button = QPushButton("Launch editor", self)
        self.launch_button.setProperty("launcherRole", "launchButton")
        self.launch_button.clicked.connect(lambda: self.launch_requested.emit(self.game))

        self.configure_button = QPushButton("Configure", self)
        self.configure_button.setProperty("launcherRole", "secondaryButton")
        self.configure_button.clicked.connect(lambda: self.configure_requested.emit(self.game))

        self.availability_button = QToolButton(self)
        self.availability_button.setText("Why unavailable?")
        self.availability_button.setIcon(action_icon("info"))
        self.availability_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.availability_button.setProperty("launcherRole", "stageWarning")
        self.availability_button.clicked.connect(
            lambda: self.configure_requested.emit(self.game)
        )

        actions = QHBoxLayout()
        actions.setSpacing(THEME.space_3)
        actions.addWidget(self.launch_button)
        actions.addWidget(self.configure_button)
        actions.addStretch()

        self.status_label = QLabel(self)
        self.status_label.setProperty("launcherRole", "worldStatus")
        self.path_label = QLabel(self)
        self.path_label.setProperty("launcherRole", "worldPath")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_8, THEME.space_7, THEME.space_8, THEME.space_7)
        layout.setSpacing(THEME.space_2)
        layout.addLayout(header)
        layout.addStretch(1)
        layout.addWidget(overline)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacing(THEME.space_3)
        layout.addWidget(self.description_label)
        layout.addSpacing(THEME.space_4)
        layout.addLayout(actions)
        layout.addWidget(self.availability_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(THEME.space_2)
        layout.addWidget(self.status_label)
        layout.addWidget(self.path_label)
        self.update_profile(profile)

    def update_profile(self, profile: GameProfile) -> None:
        specification = profile.specification
        self.game = specification.key
        self.set_world(self.game)
        self.setting_label.setText(specification.setting)
        self.title_label.setText(specification.title)
        self.subtitle_label.setText(specification.subtitle)
        self.description_label.setText(WORLD_SCENES[self.game].description)
        self.settings_button.setAccessibleName(f"Configure {specification.title}")
        self.settings_button.setToolTip(f"Configure {specification.title} game files")
        self.configure_button.setAccessibleName(f"Configure {specification.title}")
        self.launch_button.setAccessibleName(f"Launch {specification.title} editor")
        self.availability_button.setAccessibleName(
            f"Explain why {specification.title} cannot launch"
        )

        ready = profile.ready
        self.launch_button.setEnabled(ready)
        self.launch_button.setText("Launch editor" if ready else "Unavailable")
        self.availability_button.setVisible(not ready)
        self.availability_button.setToolTip("")
        self.status_label.setProperty("launcherReady", ready)
        self.status_label.setProperty("launcherWarning", not ready)

        issue = profile.issue
        if ready:
            self.status_label.setText("Ready to explore")
            self.status_label.setToolTip("")
        elif issue is not None:
            explanation = explanation_for_issue(profile, issue)
            self.status_label.setText(status_for_issue(issue))
            self.status_label.setToolTip(explanation)
            self.availability_button.setToolTip(explanation)
        else:
            self.status_label.setText("Game files are unavailable")
            self.status_label.setToolTip("")

        path = str(profile.directory) if profile.directory is not None else "No directory selected"
        available_width = max(THEME.launcher_rail_width, self.width() - 2 * THEME.space_8)
        self.path_label.setText(
            self.path_label.fontMetrics().elidedText(path, Qt.TextElideMode.ElideMiddle, available_width)
        )
        self.path_label.setToolTip(path)

        for widget in (self.status_label, self.launch_button):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
