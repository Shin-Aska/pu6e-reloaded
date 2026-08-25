from __future__ import annotations

import struct
from typing import Final

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

import mapedit_gl as renderer
from pu6e_qt.application import initialize_editor
from pu6e_qt.game_profiles import GAMES, GameProfile, GameProfileStore
from pu6e_qt.launcher_cards import GameCard
from pu6e_qt.launcher_dialog import GameConfigurationDialog
from pu6e_qt.launcher_stage import WorldStage
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
        self.selected_game = GAMES[0].key
        self.setObjectName("pu6e-launcher")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("pu6e Reloaded — Choose your world")
        self.setMinimumSize(860, 560)
        self.resize(1040, 660)
        self.setStyleSheet(launcher_stylesheet())

        rail = QWidget(self)
        rail.setObjectName("atlas-world-rail")
        rail.setFixedWidth(THEME.launcher_rail_width)

        wordmark = QLabel("pu6e.", rail)
        wordmark.setObjectName("launcher-wordmark")
        kicker = QLabel("WORLD EDITOR", rail)
        kicker.setObjectName("launcher-kicker")
        worlds = QLabel("YOUR WORLDS", rail)
        worlds.setObjectName("launcher-worlds-label")

        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(THEME.space_3, THEME.space_7, THEME.space_3, THEME.space_5)
        rail_layout.setSpacing(THEME.space_1)
        rail_layout.addWidget(wordmark)
        rail_layout.addWidget(kicker)
        rail_layout.addSpacing(THEME.space_7)
        rail_layout.addWidget(worlds)
        rail_layout.addSpacing(THEME.space_2)

        for specification in GAMES:
            card = GameCard(store.profile(specification.key), rail)
            card.configure_requested.connect(self.configure_game)
            card.selection_requested.connect(self.select_game)
            self.cards[specification.key] = card
            rail_layout.addWidget(card)
            rail_layout.addSpacing(THEME.space_1)

        rail_layout.addStretch()
        footer = QLabel("3 worlds in your library", rail)
        footer.setObjectName("launcher-footer")
        rail_layout.addWidget(footer)

        self.stage = WorldStage(store.profile(self.selected_game), self)
        self.stage.configure_requested.connect(self.configure_game)
        self.stage.launch_requested.connect(self.launch_game)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(rail)
        layout.addWidget(self.stage, 1)
        self.select_game(self.selected_game)

    def select_game(self, game: str) -> None:
        self.selected_game = game
        for key, card in self.cards.items():
            card.setChecked(key == game)
        self.stage.update_profile(self.store.profile(game))

    def configure_game(self, game: str) -> None:
        dialog = GameConfigurationDialog(self.store, game, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._refresh_profile(self.store.profile(game))

    def launch_game(self, game: str) -> None:
        profile = self.store.profile(game)
        if not profile.ready:
            self._refresh_profile(profile)
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
            self._refresh_profile(refreshed_profile)
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
            for game in self.cards:
                self._refresh_profile(self.store.profile(game))
            self.show()
        return super().eventFilter(watched, event)

    def _refresh_profile(self, profile: GameProfile) -> None:
        self.cards[profile.specification.key].update_profile(profile)
        if profile.specification.key == self.selected_game:
            self.stage.update_profile(profile)
