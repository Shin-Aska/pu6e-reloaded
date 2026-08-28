from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Final

import mapedit_gl as renderer
from U6 import Config

from pu6e_qt.configuration import migrate_legacy_configuration, user_configuration_path
from pu6e_qt.controller import EditorController
from pu6e_qt import renderer_settings

_CONFIG_PATH: Final = user_configuration_path()
_INITIAL_POSITION: Final = (0x134, 0x16C, 0)
@dataclass(frozen=True, slots=True)
class ConfigurationFileError(FileNotFoundError):
    path: Path

    def __str__(self) -> str:
        return f"required configuration file is missing: {self.path}"


@dataclass(frozen=True, slots=True)
class MalformedConfigurationError(ValueError):
    path: Path
    cause: str

    def __str__(self) -> str:
        return (
            f"configuration file is malformed: {self.path}: {self.cause}. "
            "Repair the [pu6e] settings and try again."
        )


@dataclass(frozen=True, slots=True)
class GameDirectoryError(FileNotFoundError):
    path: Path

    def __str__(self) -> str:
        return f"configured game directory is missing or not a directory: {self.path}"


@dataclass(frozen=True, slots=True)
class GameTypeError(ValueError):
    game_type: str

    def __str__(self) -> str:
        return f"configured game type is unsupported: {self.game_type}"


@dataclass(frozen=True, slots=True)
class DisplayConfigurationError(ValueError):
    width: int
    height: int
    scale: float

    def __str__(self) -> str:
        return (
            "configured width, height, and zoom must be positive: "
            f"{self.width}x{self.height} at {self.scale}"
        )


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    game_directory: Path
    game_type: str
    width: int
    height: int
    scale: float


def read_configuration(config_path: Path) -> RuntimeConfiguration:
    if not config_path.is_file():
        raise ConfigurationFileError(config_path)

    try:
        Config.read(str(config_path))
    except (configparser.Error, ValueError) as error:
        raise MalformedConfigurationError(config_path, str(error)) from error
    game_directory = Path(Config.gamedir)
    if not game_directory.is_dir():
        raise GameDirectoryError(game_directory)
    if Config.gametype not in Config.paths:
        raise GameTypeError(Config.gametype)
    if Config.screen_width <= 0 or Config.screen_height <= 0 or Config.scale_factor <= 0:
        raise DisplayConfigurationError(
            Config.screen_width,
            Config.screen_height,
            Config.scale_factor,
        )
    return RuntimeConfiguration(
        game_directory=game_directory,
        game_type=Config.gametype,
        width=Config.screen_width,
        height=Config.screen_height,
        scale=Config.scale_factor,
    )


def initialize_editor(config_path: Path = _CONFIG_PATH) -> EditorController:
    configuration = read_configuration(config_path)
    controller = EditorController()
    controller.load_game(configuration.game_directory, configuration.game_type)
    renderer.screen_width = configuration.width
    renderer.screen_height = configuration.height
    renderer.scale_factor = configuration.scale
    controller.set_position(*_INITIAL_POSITION)
    return controller


def main() -> None:
    from pu6e_qt.canvas import configure_opengl_format

    requested_renderer = renderer_settings.read_renderer_mode(_CONFIG_PATH)
    requested_vulkan_gpu = renderer_settings.read_vulkan_gpu(_CONFIG_PATH)
    runtime = renderer_settings.resolve_renderer(requested_renderer, requested_vulkan_gpu)
    renderer_settings.configure_renderer(
        runtime.renderer,
        runtime.software_vulkan,
        runtime.vulkan_gpu,
    )
    configure_opengl_format()

    from PySide6.QtWidgets import QApplication
    from pu6e_qt.game_profiles import GameProfileStore
    from pu6e_qt.launcher import LauncherWindow
    from pu6e_qt.theme import apply_theme

    application = QApplication(sys.argv)
    apply_theme(application)
    try:
        migrate_legacy_configuration(_CONFIG_PATH, Path("pu6e.conf"))
        store = GameProfileStore(_CONFIG_PATH)
    except configparser.Error as error:
        from PySide6.QtWidgets import QMessageBox

        configuration_error = MalformedConfigurationError(_CONFIG_PATH, str(error))
        QMessageBox.critical(
            None,
            "Configuration error",
            f"Repair the configuration file at {_CONFIG_PATH}: {configuration_error.cause}",
        )
        return
    if runtime.notice is not None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(None, "Renderer fallback", runtime.notice)
    window = LauncherWindow(store, runtime)
    window.show()
    application.exec()
