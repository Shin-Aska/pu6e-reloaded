from __future__ import annotations

import os
from pathlib import Path

from game.format.resources import palette_filename, required_game_files, resolve_dos_path
from ui.profile.models import (
    GAMES,
    GameProfile,
    GameProfileIssue,
    GameProfileIssueKind,
    GameSpecification,
)


def inspect_game_profile(game: str, directory: Path | None) -> GameProfile:
    specification = next(item for item in GAMES if item.key == game)
    if directory is None:
        return GameProfile(
            specification,
            None,
            (),
            GameProfileIssue(GameProfileIssueKind.UNCONFIGURED),
        )

    resolved = directory.expanduser().resolve()
    resources = required_game_files(game)
    resource_paths = {name: resolve_dos_path(resolved / name) for name in resources}
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
            (
                name
                for name in candidates
                if (path := resolve_dos_path(resolved / name)).exists()
                and not _is_readable(path)
            ),
            None,
        )
        issue = (
            GameProfileIssue(GameProfileIssueKind.PERMISSION_DENIED, (denied,))
            if denied is not None
            else _inspect_directory(specification, resolved, missing)
        )
    return GameProfile(specification, resolved, missing, issue)


def _is_readable(path: Path) -> bool:
    permissions = os.R_OK | os.X_OK if path.is_dir() else os.R_OK
    return os.access(path, permissions)


def _inspect_directory(
    game: GameSpecification,
    directory: Path,
    missing: tuple[str, ...],
) -> GameProfileIssue | None:
    savegame = resolve_dos_path(directory / "savegame")
    expected_palette = palette_filename(game.key)
    if expected_palette in missing:
        detected = tuple(
            other
            for other in GAMES
            if other.key != game.key
            and resolve_dos_path(directory / palette_filename(other.key)).is_file()
        )
        if len(detected) == 1:
            return GameProfileIssue(
                GameProfileIssueKind.WRONG_GAME,
                (expected_palette,),
                detected[0],
            )

    if expected_palette in missing:
        return GameProfileIssue(GameProfileIssueKind.MISSING_PALETTE, (expected_palette,))
    if any(not path.startswith("savegame/") for path in missing):
        return GameProfileIssue(GameProfileIssueKind.MISSING_CORE_FILES, missing)
    if not savegame.is_dir():
        return GameProfileIssue(GameProfileIssueKind.MISSING_SAVE_DIRECTORY, ("savegame",))
    if missing:
        return GameProfileIssue(GameProfileIssueKind.MISSING_SAVE_FILES, missing)
    return None
