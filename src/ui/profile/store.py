from __future__ import annotations

from pathlib import Path
from typing import final

from ui.profile.models import (
    GameProfile,
    GameUnavailableError,
)
from ui.profile.validation import inspect_game_profile
from ui.settings.store import SettingsStore


@final
class GameProfileStore:
    def __init__(self, settings: SettingsStore) -> None:
        self.settings = settings
        self._directories = dict(settings.game_directories())

    @property
    def config_path(self) -> Path:
        return self.settings.config_path

    def profile(self, game: str) -> GameProfile:
        return self.inspect(game, self._directories.get(game))

    def inspect(self, game: str, directory: Path | None) -> GameProfile:
        return inspect_game_profile(game, directory)

    def set_directory(self, game: str, directory: Path) -> None:
        resolved = directory.expanduser().resolve()
        directories = self._directories | {game: resolved}
        self.settings.set_game_directories(directories)
        self._directories = directories

    def activate(self, game: str) -> None:
        profile = self.profile(game)
        if not profile.ready or profile.directory is None:
            raise GameUnavailableError(game)
        self.settings.activate_game(game, profile.directory)
