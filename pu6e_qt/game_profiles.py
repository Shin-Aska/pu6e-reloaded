from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, assert_never

from U6 import Config, dospath, obj, pal
from pu6e_qt.renderer_settings import (
    RendererMode,
    VulkanDeviceSelector,
    read_renderer_mode,
    read_vulkan_gpu,
)


@dataclass(frozen=True, slots=True)
class GameSpecification:
    key: str
    title: str
    subtitle: str
    badge: str
    setting: str


GAMES: Final[tuple[GameSpecification, ...]] = (
    GameSpecification("fp", "Ultima VI", "The False Prophet", "VI", "BRITANNIA · 1990"),
    GameSpecification("md", "Martian Dreams", "Worlds of Ultima", "MD", "MARS · 1991"),
    GameSpecification("se", "The Savage Empire", "Worlds of Ultima", "SE", "EODON · 1990"),
)


class GameProfileIssueKind(StrEnum):
    UNCONFIGURED = "unconfigured"
    DIRECTORY_MISSING = "directory_missing"
    NOT_DIRECTORY = "not_directory"
    PERMISSION_DENIED = "permission_denied"
    WRONG_GAME = "wrong_game"
    CASE_MISMATCH = "case_mismatch"
    MISSING_PALETTE = "missing_palette"
    MISSING_CORE_FILES = "missing_core_files"
    MISSING_SAVE_DIRECTORY = "missing_save_directory"
    MISSING_SAVE_FILES = "missing_save_files"


@dataclass(frozen=True, slots=True)
class GameProfileIssue:
    kind: GameProfileIssueKind
    paths: tuple[str, ...] = ()
    detected_game: GameSpecification | None = None

    @property
    def summary(self) -> str:
        match self.kind:
            case GameProfileIssueKind.UNCONFIGURED:
                return "Not configured"
            case GameProfileIssueKind.DIRECTORY_MISSING:
                return "Game directory does not exist"
            case GameProfileIssueKind.NOT_DIRECTORY:
                return "Selected path is not a directory"
            case GameProfileIssueKind.PERMISSION_DENIED:
                return "Game files cannot be read"
            case GameProfileIssueKind.WRONG_GAME:
                return "Different game installation selected"
            case GameProfileIssueKind.CASE_MISMATCH:
                return "Game filename has incorrect capitalization"
            case GameProfileIssueKind.MISSING_PALETTE:
                return "Game palette is missing"
            case GameProfileIssueKind.MISSING_CORE_FILES:
                return "Required game files are missing"
            case GameProfileIssueKind.MISSING_SAVE_DIRECTORY:
                return "Saved game directory is missing"
            case GameProfileIssueKind.MISSING_SAVE_FILES:
                return "Saved game files are missing"
            case unreachable:
                assert_never(unreachable)

    @property
    def details(self) -> str:
        match self.kind:
            case GameProfileIssueKind.UNCONFIGURED:
                return "No game installation directory has been selected."
            case GameProfileIssueKind.WRONG_GAME:
                detected = self.detected_game
                title = detected.title if detected is not None else "another supported game"
                return f"This directory contains {title}, not the selected game."
            case GameProfileIssueKind.CASE_MISMATCH:
                return f"Expected {self.paths[0]!r}, but found {self.paths[1]!r}."
            case (GameProfileIssueKind.DIRECTORY_MISSING | GameProfileIssueKind.NOT_DIRECTORY
                  | GameProfileIssueKind.PERMISSION_DENIED | GameProfileIssueKind.MISSING_PALETTE
                  | GameProfileIssueKind.MISSING_CORE_FILES
                  | GameProfileIssueKind.MISSING_SAVE_DIRECTORY
                  | GameProfileIssueKind.MISSING_SAVE_FILES):
                blocks = tuple(path for path in self.paths if path.startswith("savegame/objblk"))
                other_paths = tuple(path for path in self.paths if path not in blocks)
                shown = list(other_paths[:5])
                if blocks:
                    shown.append(
                        f"saved-world object block ({blocks[0]})"
                        if len(blocks) == 1
                        else f"{len(blocks)} saved-world object blocks (savegame/objblk*)"
                    )
                remaining = len(other_paths) - min(len(other_paths), 5)
                if remaining:
                    shown.append(f"{remaining} additional required files")
                return ", ".join(shown)
            case unreachable:
                assert_never(unreachable)

    @property
    def remedy(self) -> str:
        match self.kind:
            case (GameProfileIssueKind.UNCONFIGURED | GameProfileIssueKind.DIRECTORY_MISSING
                  | GameProfileIssueKind.NOT_DIRECTORY | GameProfileIssueKind.WRONG_GAME):
                return "Select the complete installation directory for this game."
            case GameProfileIssueKind.PERMISSION_DENIED:
                return "Allow read access to the game directory and its required files."
            case GameProfileIssueKind.CASE_MISMATCH:
                return "Rename the game files to their expected lowercase names."
            case GameProfileIssueKind.MISSING_PALETTE | GameProfileIssueKind.MISSING_CORE_FILES:
                return "Copy a complete installation of the selected game."
            case GameProfileIssueKind.MISSING_SAVE_DIRECTORY | GameProfileIssueKind.MISSING_SAVE_FILES:
                return "Start the original game and create a save first."
            case unreachable:
                assert_never(unreachable)


@dataclass(frozen=True, slots=True)
class GameProfile:
    specification: GameSpecification
    directory: Path | None
    missing_files: tuple[str, ...]
    issue: GameProfileIssue | None = None

    @property
    def ready(self) -> bool:
        return self.directory is not None and not self.missing_files and self.issue is None


@dataclass(frozen=True, slots=True)
class GameUnavailableError(ValueError):
    game: str

    def __str__(self) -> str:
        return f"game installation is not configured and complete: {self.game}"


class GameProfileStore:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._configuration = ConfigParser()
        self._configuration.read(config_path)
        self._directories: dict[str, Path] = {}
        self.renderer = read_renderer_mode(config_path)
        self.vulkan_gpu = read_vulkan_gpu(config_path)

        if self._configuration.has_section("pu6e"):
            game = self._configuration.get("pu6e", "gametype", fallback="fp")
            directory = self._configuration.get("pu6e", "gamedir", fallback="")
            if game in Config.paths and directory:
                self._directories[game] = self._resolve(directory)

        for specification in GAMES:
            directory = self._configuration.get(f"game:{specification.key}", "gamedir", fallback="")
            if directory:
                self._directories[specification.key] = self._resolve(directory)

    def profile(self, game: str) -> GameProfile:
        return self.inspect(game, self._directories.get(game))

    def inspect(self, game: str, directory: Path | None) -> GameProfile:
        specification = next(item for item in GAMES if item.key == game)
        if directory is None:
            return GameProfile(
                specification, None, (), GameProfileIssue(GameProfileIssueKind.UNCONFIGURED)
            )

        resolved = directory.expanduser().resolve()
        resources = {
            "basetile",
            "chunks",
            "map",
            "savegame/objlist",
            pal.paths[game],
            *(filename for filename, encoding in Config.paths[game].values()
              if not encoding & Config.EMPTY),
            *(f"savegame/objblk{obj.block_num_to_id(block)}" for block in range(69)),
        }
        if game == "fp":
            resources.add("book.dat")
        resource_paths = {name: dospath.resolve_dos_path(resolved / name) for name in resources}
        missing = tuple(sorted(name for name, path in resource_paths.items() if not path.is_file()))

        if not resolved.exists():
            issue = GameProfileIssue(GameProfileIssueKind.DIRECTORY_MISSING, (str(resolved),))
        elif not resolved.is_dir():
            issue = GameProfileIssue(GameProfileIssueKind.NOT_DIRECTORY, (str(resolved),))
        elif not _is_readable(resolved):
            issue = GameProfileIssue(GameProfileIssueKind.PERMISSION_DENIED, (str(resolved),))
        else:
            candidates = ("savegame", *sorted(resources))
            denied = next(
                (name for name in candidates
                 if (path := dospath.resolve_dos_path(resolved / name)).exists()
                 and not _is_readable(path)),
                None,
            )
            issue = (
                GameProfileIssue(GameProfileIssueKind.PERMISSION_DENIED, (denied,))
                if denied is not None
                else _inspect_directory(specification, resolved, missing)
            )
        return GameProfile(specification, resolved, missing, issue)

    def set_directory(self, game: str, directory: Path) -> None:
        self._directories[game] = directory.expanduser().resolve()
        self._write()

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
        previous_renderer = self._configuration.get(
            "launcher",
            "renderer",
            fallback=None,
        )
        previous_vulkan_gpu = self._configuration.get(
            "launcher",
            "vulkan_gpu",
            fallback=None,
        )
        self._configuration.set("launcher", "renderer", renderer.value)
        self._configuration.set(
            "launcher",
            "vulkan_gpu",
            vulkan_gpu if vulkan_gpu is not None else "auto",
        )
        try:
            self._write()
        except OSError:
            for name, previous in (
                ("renderer", previous_renderer),
                ("vulkan_gpu", previous_vulkan_gpu),
            ):
                if previous is None:
                    self._configuration.remove_option("launcher", name)
                else:
                    self._configuration.set("launcher", name, previous)
            if not had_section:
                self._configuration.remove_section("launcher")
            raise
        self.renderer = renderer
        self.vulkan_gpu = vulkan_gpu

    def activate(self, game: str) -> None:
        profile = self.profile(game)
        if not profile.ready or profile.directory is None:
            raise GameUnavailableError(game)
        if not self._configuration.has_section("pu6e"):
            self._configuration.add_section("pu6e")

        section = self._configuration["pu6e"]
        section["gamedir"] = str(profile.directory)
        section["gametype"] = game
        for name, fallback in (("width", "1024"), ("height", "768"), ("zoom", "1")):
            if name not in section:
                section[name] = fallback
        self._write()

    def _resolve(self, directory: str) -> Path:
        path = Path(directory).expanduser()
        if not path.is_absolute():
            path = self.config_path.parent / path
        return path.resolve()

    def _write(self) -> None:
        for game, directory in self._directories.items():
            section = f"game:{game}"
            if not self._configuration.has_section(section):
                self._configuration.add_section(section)
            self._configuration.set(section, "gamedir", str(directory))
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as destination:
            self._configuration.write(destination)


def _is_readable(path: Path) -> bool:
    permissions = os.R_OK | os.X_OK if path.is_dir() else os.R_OK
    return os.access(path, permissions)


def _inspect_directory(
    game: GameSpecification, directory: Path, missing: tuple[str, ...]
) -> GameProfileIssue | None:
    savegame = dospath.resolve_dos_path(directory / "savegame")
    expected_palette = pal.paths[game.key]
    if expected_palette in missing:
        detected = tuple(
            other
            for other in GAMES
            if other.key != game.key
            and dospath.resolve_dos_path(directory / pal.paths[other.key]).is_file()
        )
        if len(detected) == 1:
            return GameProfileIssue(GameProfileIssueKind.WRONG_GAME, (expected_palette,), detected[0])

    if expected_palette in missing:
        return GameProfileIssue(GameProfileIssueKind.MISSING_PALETTE, (expected_palette,))
    if any(not path.startswith("savegame/") for path in missing):
        return GameProfileIssue(GameProfileIssueKind.MISSING_CORE_FILES, missing)
    if not savegame.is_dir():
        return GameProfileIssue(GameProfileIssueKind.MISSING_SAVE_DIRECTORY, ("savegame",))
    if missing:
        return GameProfileIssue(GameProfileIssueKind.MISSING_SAVE_FILES, missing)
    return None
