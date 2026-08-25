from __future__ import annotations

from typing import assert_never

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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


class GameCard(QPushButton):
    selection_requested = Signal(str)
    configure_requested = Signal(str)

    def __init__(self, profile: GameProfile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.game = profile.specification.key
        self.setObjectName(f"game-card-{self.game}")
        self.setProperty("launcherRole", "gameCard")
        self.setAccessibleName(f"Select {profile.specification.title}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.selection_requested.emit(self.game))

        badge = QLabel(profile.specification.badge, self)
        badge.setProperty("launcherRole", "gameBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(THEME.space_8, THEME.space_8 + THEME.space_2)

        title = QLabel(profile.specification.title, self)
        title.setProperty("launcherRole", "gameRailTitle")
        title.setWordWrap(True)

        self.status_label = QLabel(self)
        self.status_label.setProperty("launcherRole", "gameStatus")
        self.status_label.setWordWrap(True)

        title_column = QVBoxLayout()
        title_column.setSpacing(THEME.space_1)
        title_column.addWidget(title)
        title_column.addWidget(self.status_label)

        self.settings_button = QToolButton(self)
        self.settings_button.setIcon(action_icon("settings"))
        self.settings_button.setProperty("launcherRole", "settingsButton")
        self.settings_button.setAccessibleName(f"Configure {profile.specification.title}")
        self.settings_button.setToolTip(f"Configure {profile.specification.title} game files")
        self.settings_button.setFixedSize(THEME.space_6 + THEME.space_1, THEME.space_6 + THEME.space_1)
        self.settings_button.clicked.connect(lambda: self.configure_requested.emit(self.game))

        self.availability_button = QToolButton(self)
        self.availability_button.setIcon(action_icon("info"))
        self.availability_button.setProperty("launcherRole", "warningButton")
        self.availability_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.availability_button.setFixedSize(THEME.space_6 + THEME.space_1, THEME.space_6 + THEME.space_1)
        self.availability_button.setAccessibleName(
            f"Explain why {profile.specification.title} cannot launch"
        )
        self.availability_button.clicked.connect(
            lambda: self.configure_requested.emit(self.game)
        )

        utility = QVBoxLayout()
        utility.setSpacing(THEME.space_1)
        utility.addWidget(self.settings_button)
        utility.addWidget(self.availability_button)
        utility.addStretch()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(THEME.space_2, THEME.space_3, THEME.space_1, THEME.space_3)
        layout.setSpacing(THEME.space_2)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_column, 1)
        layout.addLayout(utility)
        self.update_profile(profile)

    def update_profile(self, profile: GameProfile) -> None:
        ready = profile.ready
        issue = profile.issue
        warning = not ready
        self.setProperty("launcherReady", ready)
        self.status_label.setProperty("launcherReady", ready)
        self.status_label.setProperty("launcherWarning", warning)
        self.availability_button.setVisible(warning)
        self.availability_button.setToolTip("")
        self.status_label.setToolTip("")

        if ready:
            self.status_label.setText("Ready")
        elif issue is None:
            self.status_label.setText("Game files are unavailable")
        else:
            self.status_label.setText(status_for_issue(issue))
            explanation = explanation_for_issue(profile, issue)
            self.availability_button.setToolTip(explanation)
            self.status_label.setToolTip(explanation)
        self.setAccessibleDescription(self.status_label.text())
        self.setMinimumHeight(self.layout().minimumSize().height())

        for widget in (self, self.status_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


def status_for_issue(issue: GameProfileIssue) -> str:
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


def explanation_for_issue(profile: GameProfile, issue: GameProfileIssue) -> str:
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
