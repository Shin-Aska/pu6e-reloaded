from __future__ import annotations

import configparser
import sys
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Final

from game.format.resources import SUPPORTED_GAMES
from ui.runtime import renderer as renderer_runtime
from ui.runtime.vulkan import read_vulkan_gpu
from ui.settings.paths import migrate_legacy_configuration, user_configuration_path
from ui.settings.renderer import read_renderer_mode
from ui.settings.store import SettingsStore

if TYPE_CHECKING:
    from ui.app.controller import EditorController

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
    from ui.app.controller import EditorController

    configuration = read_configuration(config_path)
    controller = EditorController()
    controller.load_game(configuration.game_directory, configuration.game_type)
    controller.camera.resize(configuration.width, configuration.height)
    controller.camera.set_zoom(configuration.scale)
    controller.set_position(*_INITIAL_POSITION)
    return controller


def main() -> None:
    runtime = renderer_runtime.resolve_renderer(
        read_renderer_mode(_CONFIG_PATH),
        read_vulkan_gpu(_CONFIG_PATH),
    )
    renderer_runtime.configure_renderer(
        runtime.renderer,
        runtime.software_vulkan,
        runtime.vulkan_gpu,
    )
    from ui.runtime.surface import configure_opengl_format

    configure_opengl_format()

    from PySide6.QtWidgets import QApplication

    from ui.launcher.window import LauncherWindow
    from ui.profile.store import GameProfileStore
    from ui.runtime.restart import restart_application
    from ui.shared.theme import apply_theme

    application = QApplication(sys.argv)
    apply_theme(application)
    try:
        migrate_legacy_configuration(_CONFIG_PATH, Path("pu6e.conf"))
        settings = SettingsStore(_CONFIG_PATH)
        store = GameProfileStore(settings)
    except configparser.Error as error:
        from PySide6.QtWidgets import QMessageBox

        configuration_error = MalformedConfigurationError(_CONFIG_PATH, str(error))
        QMessageBox.critical(
            None,
            "Configuration error",
            f"Repair the configuration file at {_CONFIG_PATH}: {configuration_error.cause}",
        )
        return
    window = LauncherWindow(
        store,
        settings,
        runtime,
        launch_editor=initialize_editor,
        restart_application=restart_application,
    )
    window.show()
    if runtime.notice is not None:
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(window, "Renderer fallback", runtime.notice)
    application.exec()
