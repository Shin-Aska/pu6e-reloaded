from __future__ import annotations

from collections.abc import Mapping
from configparser import ConfigParser
from pathlib import Path
from typing import final

from game.format.resources import SUPPORTED_GAMES
from ui.runtime.vulkan import VulkanDeviceSelector, parse_vulkan_device_selector
from ui.settings.renderer import RendererMode, parse_renderer_mode


@final
class SettingsStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._configuration = ConfigParser()
        _ = self._configuration.read(config_path, encoding="utf-8")

    @property
    def renderer(self) -> RendererMode:
        return parse_renderer_mode(
            self._configuration.get("launcher", "renderer", fallback=None)
        )

    @property
    def vulkan_gpu(self) -> VulkanDeviceSelector | None:
        value = self._configuration.get("launcher", "vulkan_gpu", fallback="auto")
        return parse_vulkan_device_selector(value)

    def game_directories(self) -> Mapping[str, Path]:
        directories: dict[str, Path] = {}
        if self._configuration.has_section("pu6e"):
            game = self._configuration.get("pu6e", "gametype", fallback="fp")
            directory = self._configuration.get("pu6e", "gamedir", fallback="")
            if game in SUPPORTED_GAMES and directory:
                directories[game] = self._resolve(directory)
        for game in SUPPORTED_GAMES:
            directory = self._configuration.get(f"game:{game}", "gamedir", fallback="")
            if directory:
                directories[game] = self._resolve(directory)
        return directories

    def set_game_directories(self, directories: Mapping[str, Path]) -> None:
        previous: dict[str, tuple[bool, str | None]] = {}
        for game, directory in directories.items():
            section_name = f"game:{game}"
            had_section = self._configuration.has_section(section_name)
            previous[section_name] = (
                had_section,
                self._configuration.get(section_name, "gamedir", fallback=None),
            )
            if not had_section:
                self._configuration.add_section(section_name)
            self._configuration.set(section_name, "gamedir", str(directory))
        try:
            self._write()
        except OSError:
            for section_name, (had_section, prior_directory) in previous.items():
                self._restore_option(
                    section_name,
                    "gamedir",
                    prior_directory,
                    had_section,
                )
            raise

    def activate_game(self, game: str, directory: Path) -> None:
        had_section = self._configuration.has_section("pu6e")
        previous = dict(self._configuration["pu6e"]) if had_section else None
        if not had_section:
            self._configuration.add_section("pu6e")
        section = self._configuration["pu6e"]
        section["gamedir"] = str(directory)
        section["gametype"] = game
        for name, fallback in (("width", "1024"), ("height", "768"), ("zoom", "1")):
            if name not in section:
                section[name] = fallback
        try:
            self._write()
        except OSError:
            _ = self._configuration.remove_section("pu6e")
            if previous is not None:
                self._configuration.read_dict({"pu6e": previous})
            raise

    def set_renderer(self, renderer: RendererMode) -> None:
        self.set_renderer_preferences(renderer, self.vulkan_gpu)

    def set_renderer_preferences(
        self,
        renderer: RendererMode,
        vulkan_gpu: VulkanDeviceSelector | None,
    ) -> None:
        had_section = self._configuration.has_section("launcher")
        if not had_section:
            self._configuration.add_section("launcher")
        previous_renderer = self._configuration.get("launcher", "renderer", fallback=None)
        previous_vulkan_gpu = self._configuration.get("launcher", "vulkan_gpu", fallback=None)
        self._configuration.set("launcher", "renderer", renderer.value)
        self._configuration.set(
            "launcher",
            "vulkan_gpu",
            vulkan_gpu if vulkan_gpu is not None else "auto",
        )
        try:
            self._write()
        except OSError:
            self._restore_option("launcher", "renderer", previous_renderer, True)
            self._restore_option("launcher", "vulkan_gpu", previous_vulkan_gpu, had_section)
            raise

    def _resolve(self, directory: str) -> Path:
        path = Path(directory).expanduser()
        if not path.is_absolute():
            path = self.config_path.parent / path
        return path.resolve()

    def _restore_option(
        self,
        section: str,
        name: str,
        previous: str | None,
        keep_section: bool,
    ) -> None:
        if previous is None:
            _ = self._configuration.remove_option(section, name)
        else:
            self._configuration.set(section, name, previous)
        if not keep_section and not self._configuration.options(section):
            _ = self._configuration.remove_section(section)

    def _write(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as destination:
            self._configuration.write(destination)
