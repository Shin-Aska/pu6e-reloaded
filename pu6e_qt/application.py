from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Final

import mapedit_gl as renderer
from U6 import Config

from pu6e_qt.controller import EditorController

_CONFIG_PATH: Final = Path("pu6e.conf")
_INITIAL_POSITION: Final = (0x134, 0x16C, 0)
_MINIMUM_WINDOW_SIZE: Final = (1120, 760)


@dataclass(frozen=True, slots=True)
class ConfigurationFileError(FileNotFoundError):
    path: Path

    def __str__(self) -> str:
        return f"required configuration file is missing: {self.path}"


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

    Config.read(str(config_path))
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

    configure_opengl_format()

    from PySide6.QtWidgets import QApplication
    from pu6e_qt.main_window import MainWindow
    from pu6e_qt.theme import apply_theme

    application = QApplication(sys.argv)
    apply_theme(application)
    controller = initialize_editor()
    window = MainWindow(controller)
    window.resize(
        max(renderer.screen_width, _MINIMUM_WINDOW_SIZE[0]),
        max(renderer.screen_height, _MINIMUM_WINDOW_SIZE[1]),
    )
    window.show()
    application.exec()
