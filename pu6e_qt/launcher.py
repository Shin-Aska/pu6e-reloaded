from __future__ import annotations

import struct
from typing import Final

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QLabel, QMessageBox, QVBoxLayout, QWidget

import mapedit_gl as renderer
from pu6e_qt.application import initialize_editor
from pu6e_qt.game_profiles import GAMES, GameProfileStore
from pu6e_qt.launcher_cards import GameCard
from pu6e_qt.launcher_dialog import GameConfigurationDialog
from pu6e_qt.launcher_style import launcher_stylesheet
from pu6e_qt.main_window import MainWindow
from pu6e_qt.theme import THEME

_MINIMUM_EDITOR_SIZE: Final = (1120, 760)


class LauncherWindow(QWidget):
    def __init__(self, store: GameProfileStore) -> None:
        super().__init__()
        self.store = store
        self.cards: dict[str, GameCard] = {}
        self.editor_window: MainWindow | None = None
        self.setObjectName("pu6e-launcher")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("pu6e Reloaded — Choose your world")
        self.setMinimumSize(560, 680)
        self.resize(660, 760)
        self.setStyleSheet(launcher_stylesheet())

        kicker = QLabel("ULTIMA WORLD EDITOR", self)
        kicker.setObjectName("launcher-kicker")
        wordmark = QLabel("pu6e Reloaded", self)
        wordmark.setObjectName("launcher-wordmark")
        description = QLabel("Choose a world to explore and edit.", self)
        description.setObjectName("launcher-description")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 40, 44, 32)
        layout.setSpacing(THEME.space_2)
        layout.addWidget(kicker)
        layout.addWidget(wordmark)
        layout.addWidget(description)
        layout.addSpacing(THEME.space_5)

        for specification in GAMES:
            card = GameCard(store.profile(specification.key), self)
            card.configure_requested.connect(self.configure_game)
            card.launch_requested.connect(self.launch_game)
            self.cards[specification.key] = card
            layout.addWidget(card)
            layout.addSpacing(THEME.space_2)

        layout.addStretch()
        footer = QLabel("YOUR GAME DATA STAYS ON THIS COMPUTER", self)
        footer.setObjectName("launcher-footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def configure_game(self, game: str) -> None:
        dialog = GameConfigurationDialog(self.store, game, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.cards[game].update_profile(self.store.profile(game))

    def launch_game(self, game: str) -> None:
        profile = self.store.profile(game)
        if not profile.ready:
            self.cards[game].update_profile(profile)
            issue = profile.issue
            assert issue is not None
            QMessageBox.critical(
                self,
                f"{profile.specification.title} cannot launch",
                "\n".join(
                    (
                        f"{profile.specification.title} cannot launch.",
                        "",
                        issue.summary,
                        issue.details,
                        "",
                        issue.remedy,
                    )
                ),
            )
            return

        try:
            self.store.activate(game)
            controller = initialize_editor(self.store.config_path)
        except (OSError, ValueError, struct.error) as error:
            refreshed_profile = self.store.profile(game)
            self.cards[game].update_profile(refreshed_profile)
            QMessageBox.critical(
                self,
                f"{profile.specification.title} could not launch",
                "\n".join(
                    (
                        f"{profile.specification.title} could not launch from "
                        f"{refreshed_profile.directory or self.store.config_path}.",
                        "",
                        str(error),
                        "",
                        "Check the selected game files and configuration, then repair "
                        "the problem and try again.",
                    )
                ),
            )
            return

        window = MainWindow(controller)
        window.resize(
            max(renderer.screen_width, _MINIMUM_EDITOR_SIZE[0]),
            max(renderer.screen_height, _MINIMUM_EDITOR_SIZE[1]),
        )
        self.editor_window = window
        window.installEventFilter(self)
        window.show()
        self.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.editor_window and event.type() == QEvent.Type.Close:
            for game, card in self.cards.items():
                card.update_profile(self.store.profile(game))
            self.show()
        return super().eventFilter(watched, event)
