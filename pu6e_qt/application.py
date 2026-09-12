from __future__ import annotations

import configparser
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pu6e_core.formats.resources import SUPPORTED_GAMES
from pu6e_qt import renderer_settings
from pu6e_qt.configuration import migrate_legacy_configuration, user_configuration_path

if TYPE_CHECKING:
    from pu6e_qt.controller import EditorController

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
        parser = configparser.ConfigParser()
        parser.read(config_path)
        section = parser["pu6e"]
        game_directory = Path(section["gamedir"])
        game_type = section["gametype"]
        width = parser.getint("pu6e", "width")
        height = parser.getint("pu6e", "height")
        scale = parser.getfloat("pu6e", "zoom")
    except (configparser.Error, ValueError, KeyError) as error:
        raise MalformedConfigurationError(config_path, str(error)) from error
    if not game_directory.is_dir():
        raise GameDirectoryError(game_directory)
    if game_type not in SUPPORTED_GAMES:
        raise GameTypeError(game_type)
    if width <= 0 or height <= 0 or not isfinite(scale) or scale <= 0:
        raise DisplayConfigurationError(
            width,
            height,
            scale,
        )
    return RuntimeConfiguration(
        game_directory=game_directory,
        game_type=game_type,
        width=width,
        height=height,
        scale=scale,
    )


def initialize_editor(config_path: Path = _CONFIG_PATH) -> EditorController:
    from pu6e_qt.controller import EditorController

    configuration = read_configuration(config_path)
    controller = EditorController()
    controller.load_game(configuration.game_directory, configuration.game_type)
    controller.camera.resize(configuration.width, configuration.height)
    controller.camera.set_zoom(configuration.scale)
    controller.set_position(*_INITIAL_POSITION)
    return controller


def main() -> None:
    requested_renderer = renderer_settings.read_renderer_mode(_CONFIG_PATH)
    requested_vulkan_gpu = renderer_settings.read_vulkan_gpu(_CONFIG_PATH)
    runtime = renderer_settings.resolve_renderer(requested_renderer, requested_vulkan_gpu)
    renderer_settings.configure_renderer(
        runtime.renderer,
        runtime.software_vulkan,
        runtime.vulkan_gpu,
    )
    from pu6e_qt.canvas import configure_opengl_format

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
    window = LauncherWindow(store, runtime)
    window.show()
    if runtime.notice is not None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(window, "Renderer fallback", runtime.notice)
    application.exec()
