from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, assert_never


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
            case (
                GameProfileIssueKind.DIRECTORY_MISSING
                | GameProfileIssueKind.NOT_DIRECTORY
                | GameProfileIssueKind.PERMISSION_DENIED
                | GameProfileIssueKind.MISSING_PALETTE
                | GameProfileIssueKind.MISSING_CORE_FILES
                | GameProfileIssueKind.MISSING_SAVE_DIRECTORY
                | GameProfileIssueKind.MISSING_SAVE_FILES
            ):
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
            case (
                GameProfileIssueKind.UNCONFIGURED
                | GameProfileIssueKind.DIRECTORY_MISSING
                | GameProfileIssueKind.NOT_DIRECTORY
                | GameProfileIssueKind.WRONG_GAME
            ):
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
