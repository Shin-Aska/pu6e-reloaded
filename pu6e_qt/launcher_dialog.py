from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pu6e_qt.game_profiles import GameProfileStore
from pu6e_qt.icons import action_icon
from pu6e_qt.launcher_style import launcher_stylesheet
from pu6e_qt.theme import THEME


class GameConfigurationDialog(QDialog):
    def __init__(
        self,
        store: GameProfileStore,
        game: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = store
        self.game = game
        profile = store.profile(game)
        self.setObjectName("game-configurator")
        self.setWindowTitle(f"Configure {profile.specification.title}")
        self.setMinimumWidth(540)
        self.setStyleSheet(launcher_stylesheet())

        title = QLabel(profile.specification.title, self)
        title.setProperty("launcherRole", "gameTitle")
        subtitle = QLabel("Choose a complete, disposable copy of the game installation.", self)
        subtitle.setWordWrap(True)

        directory_label = QLabel("GAME DATA DIRECTORY", self)
        directory_label.setProperty("launcherRole", "gameSetting")
        self.directory_field = QLineEdit(self)
        self.directory_field.setPlaceholderText("Select the folder containing the game files")
        self.directory_field.setAccessibleName(f"{profile.specification.title} game directory")

        browse = QPushButton(action_icon("folder"), "Browse", self)
        browse.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.directory_field, 1)
        path_row.addWidget(browse)

        self.status_label = QLabel(self)
        self.status_label.setObjectName("configuration-status")
        self.status_label.setWordWrap(True)
        guidance = QLabel(
            "The editor modifies original game data when you save. "
            "Always use a backed-up working copy.",
            self,
        )
        guidance.setObjectName("configuration-guidance")
        guidance.setWordWrap(True)

        cancel = QPushButton("Cancel", self)
        cancel.clicked.connect(self.reject)
        self.save_button = QPushButton("Save configuration", self)
        self.save_button.setProperty("launcherRole", "launchButton")
        self.save_button.clicked.connect(self._save)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(self.save_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(THEME.space_6, THEME.space_6, THEME.space_6, THEME.space_6)
        layout.setSpacing(THEME.space_3)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(THEME.space_2)
        layout.addWidget(directory_label)
        layout.addLayout(path_row)
        layout.addWidget(self.status_label)
        layout.addWidget(guidance)
        layout.addSpacing(THEME.space_2)
        layout.addLayout(buttons)

        self.directory_field.textChanged.connect(self._validate)
        if profile.directory is not None:
            self.directory_field.setText(str(profile.directory))
        else:
            self._validate("")

    def _browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Choose the game data directory", self.directory_field.text()
        )
        if directory:
            self.directory_field.setText(directory)

    def _validate(self, value: str) -> None:
        if not value.strip():
            self._show_status("Select a game directory to validate its files.")
            self.save_button.setEnabled(False)
            return

        profile = self.store.inspect(self.game, Path(value.strip()))
        self.save_button.setEnabled(profile.ready)
        if profile.ready:
            self._show_status("Installation verified. All required game files are present.")
            return

        issue = profile.issue
        if issue is None:
            self._show_status("Installation could not be verified. Select a complete game directory.")
            return

        detected = (
            f"Expected {profile.specification.title}; detected {issue.detected_game.title}."
            if issue.detected_game is not None
            else ""
        )
        self._show_status(
            "\n".join(
                line
                for line in (
                    f"{issue.summary}.",
                    f"Selected: {profile.directory}",
                    f"Affected: {issue.details}.",
                    detected,
                    issue.remedy,
                )
                if line
            )
        )

    def _show_status(self, text: str) -> None:
        self.status_label.setText(text)
        width = (
            self.status_label.width()
            if self.isVisible()
            else self.minimumWidth() - 2 * THEME.space_6
        )
        self.status_label.setMinimumHeight(self.status_label.heightForWidth(width))
        self.adjustSize()

    def _save(self) -> None:
        try:
            self.store.set_directory(self.game, Path(self.directory_field.text().strip()))
        except OSError as error:
            detail = str(error) or error.__class__.__name__
            self._show_status(
                f"Unable to save configuration to {self.store.config_path}: {detail}. "
                "Check that the configuration file and its parent directory allow write access, then try again."
            )
            return
        self.accept()
