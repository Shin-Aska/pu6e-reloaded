from __future__ import annotations

from typing import assert_never

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pu6e_qt.game_profiles import GameProfile, GameProfileIssue, GameProfileIssueKind
from pu6e_qt.icons import action_icon
from pu6e_qt.theme import THEME


class GameCard(QFrame):
    launch_requested = Signal(str)
    configure_requested = Signal(str)

    def __init__(self, profile: GameProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = profile.specification.key
        self.setObjectName(f"game-card-{self.game}")
        self.setProperty("launcherRole", "gameCard")

        badge = QLabel(profile.specification.badge, self)
        badge.setProperty("launcherRole", "gameBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(56, 56)

        setting = QLabel(profile.specification.setting, self)
        setting.setProperty("launcherRole", "gameSetting")
        title = QLabel(profile.specification.title, self)
        title.setProperty("launcherRole", "gameTitle")
        subtitle = QLabel(profile.specification.subtitle, self)
        subtitle.setProperty("launcherRole", "gameSubtitle")

        title_column = QVBoxLayout()
        title_column.setSpacing(2)
        title_column.addWidget(setting)
        title_column.addWidget(title)
        title_column.addWidget(subtitle)

        self.settings_button = QToolButton(self)
        self.settings_button.setIcon(action_icon("settings"))
        self.settings_button.setProperty("launcherRole", "settingsButton")
        self.settings_button.setAccessibleName(f"Configure {profile.specification.title}")
        self.settings_button.setToolTip(f"Configure {profile.specification.title} game files")
        self.settings_button.clicked.connect(lambda: self.configure_requested.emit(self.game))

        heading = QHBoxLayout()
        heading.setSpacing(THEME.space_3)
        heading.addWidget(badge)
        heading.addLayout(title_column, 1)
        heading.addWidget(self.settings_button, 0, Qt.AlignmentFlag.AlignTop)

        self.status_label = QLabel(self)
        self.status_label.setProperty("launcherRole", "gameStatus")
        self.path_label = QLabel(self)
        self.path_label.setProperty("launcherRole", "gamePath")
        self.path_label.setWordWrap(False)

        details = QVBoxLayout()
        details.setSpacing(THEME.space_1)
        details.addWidget(self.status_label)
        details.addWidget(self.path_label)

        self.launch_button = QPushButton("Launch editor", self)
        self.launch_button.setProperty("launcherRole", "launchButton")
        self.launch_button.setAccessibleName(f"Launch {profile.specification.title} editor")
        self.launch_button.clicked.connect(lambda: self.launch_requested.emit(self.game))

        self.availability_button = QToolButton(self)
        self.availability_button.setText("Why unavailable?")
        self.availability_button.setIcon(action_icon("info"))
        self.availability_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.availability_button.setProperty("launcherRole", "warningButton")
        self.availability_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.availability_button.setAccessibleName(
            f"Explain why {profile.specification.title} cannot launch"
        )
        self.availability_button.clicked.connect(
            lambda: self.configure_requested.emit(self.game)
        )

        bottom = QHBoxLayout()
        bottom.addLayout(details, 1)
        bottom.addWidget(self.launch_button, 0, Qt.AlignmentFlag.AlignBottom)
        bottom.addWidget(self.availability_button, 0, Qt.AlignmentFlag.AlignBottom)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_5, THEME.space_4, THEME.space_5, THEME.space_4)
        layout.setSpacing(THEME.space_3)
        layout.addLayout(heading)
        layout.addLayout(bottom)
        self.update_profile(profile)

    def update_profile(self, profile: GameProfile) -> None:
        ready = profile.ready
        issue = profile.issue
        warning = not ready
        self.setProperty("launcherReady", ready)
        self.status_label.setProperty("launcherReady", ready)
        self.status_label.setProperty("launcherWarning", warning)
        self.launch_button.setVisible(ready)
        self.availability_button.setVisible(warning)
        self.availability_button.setToolTip("")
        self.status_label.setToolTip("")

        if profile.directory is None:
            self.path_label.setText("Choose a game directory to get started")
            self.path_label.setToolTip("")
        else:
            full_path = str(profile.directory)
            self.path_label.setText(
                self.path_label.fontMetrics().elidedText(
                    full_path, Qt.TextElideMode.ElideMiddle, 340
                )
            )
            self.path_label.setToolTip(full_path)

        if ready:
            self.status_label.setText("Ready to launch")
        elif issue is None:
            self.status_label.setText("Game files are unavailable")
        else:
            self.status_label.setText(_status_for_issue(issue))
            explanation = _explanation_for_issue(profile, issue)
            self.availability_button.setToolTip(explanation)
            self.status_label.setToolTip(explanation)

        for widget in (self, self.status_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


def _status_for_issue(issue: GameProfileIssue) -> str:
    match issue.kind:
        case GameProfileIssueKind.MISSING_SAVE_DIRECTORY | GameProfileIssueKind.MISSING_SAVE_FILES:
            return "Saved game required"
        case (
            GameProfileIssueKind.UNCONFIGURED
            | GameProfileIssueKind.DIRECTORY_MISSING
            | GameProfileIssueKind.NOT_DIRECTORY
            | GameProfileIssueKind.PERMISSION_DENIED
            | GameProfileIssueKind.WRONG_GAME
            | GameProfileIssueKind.CASE_MISMATCH
            | GameProfileIssueKind.MISSING_PALETTE
            | GameProfileIssueKind.MISSING_CORE_FILES
        ):
            return issue.summary
        case unreachable:
            assert_never(unreachable)


def _explanation_for_issue(profile: GameProfile, issue: GameProfileIssue) -> str:
    details = _details_for_issue(profile, issue)
    return "\n\n".join(
        (
            f"{profile.specification.title} cannot launch.",
            issue.summary,
            details,
            issue.remedy,
        )
    )


def _details_for_issue(profile: GameProfile, issue: GameProfileIssue) -> str:
    match issue.kind:
        case (
            GameProfileIssueKind.DIRECTORY_MISSING
            | GameProfileIssueKind.NOT_DIRECTORY
            | GameProfileIssueKind.PERMISSION_DENIED
        ):
            directory = profile.directory
            return issue.details if directory is None else f"Selected game directory: {directory}\n{issue.details}"
        case (
            GameProfileIssueKind.UNCONFIGURED
            | GameProfileIssueKind.WRONG_GAME
            | GameProfileIssueKind.CASE_MISMATCH
            | GameProfileIssueKind.MISSING_PALETTE
            | GameProfileIssueKind.MISSING_CORE_FILES
            | GameProfileIssueKind.MISSING_SAVE_DIRECTORY
            | GameProfileIssueKind.MISSING_SAVE_FILES
        ):
            return issue.details
        case unreachable:
            assert_never(unreachable)
