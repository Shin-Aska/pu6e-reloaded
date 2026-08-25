from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pu6e_qt import game_profiles
from pu6e_qt.game_profiles import GameProfile, GameProfileStore
from test_core import write_game_fixture
from U6 import pal

GAMES = ("fp", "md", "se")


def _installation(tmp_path: Path, game: str) -> tuple[GameProfileStore, Path]:
    directory = tmp_path / game
    write_game_fixture(directory, game, game)
    return GameProfileStore(tmp_path / "pu6e.conf"), directory


@pytest.mark.parametrize("game", GAMES)
def test_profile_reports_unconfigured_for_each_game(tmp_path: Path, game: str) -> None:
    store = GameProfileStore(tmp_path / "pu6e.conf")

    profile = store.profile(game)

    assert profile.issue is not None
    assert profile.issue.kind.value == "unconfigured"
    assert profile.missing_files == ()
    assert not profile.ready


@pytest.mark.parametrize("game", GAMES)
def test_profile_distinguishes_missing_directory_for_each_game(tmp_path: Path, game: str) -> None:
    store = GameProfileStore(tmp_path / "pu6e.conf")
    directory = tmp_path / "absent"

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "directory_missing"
    assert profile.issue.paths == (str(directory.resolve()),)
    assert pal.paths[game] in profile.missing_files


@pytest.mark.parametrize("game", GAMES)
def test_profile_distinguishes_regular_file_for_each_game(tmp_path: Path, game: str) -> None:
    store = GameProfileStore(tmp_path / "pu6e.conf")
    regular_file = tmp_path / "regular-file"
    regular_file.write_bytes(b"not a directory")

    profile = store.inspect(game, regular_file)

    assert profile.issue is not None
    assert profile.issue.kind.value == "not_directory"
    assert profile.issue.paths == (str(regular_file),)


@pytest.mark.parametrize("game", GAMES)
def test_profile_reports_unreadable_directory_for_each_game(
    tmp_path: Path, game: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, directory = _installation(tmp_path, game)
    monkeypatch.setattr(game_profiles, "_is_readable", lambda path: path != directory)

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "permission_denied"
    assert profile.issue.paths == (str(directory),)
    assert not profile.ready


@pytest.mark.parametrize(
    "case", tuple((game, resource) for game in GAMES for resource in ("tileflag", "savegame"))
)
def test_profile_reports_unreadable_required_file_for_each_game(
    tmp_path: Path, case: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    game, denied_resource = case
    store, directory = _installation(tmp_path, game)
    denied_path = directory / denied_resource
    monkeypatch.setattr(game_profiles, "_is_readable", lambda path: path != denied_path)

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "permission_denied"
    assert profile.issue.paths == (denied_resource,)
    assert not profile.ready


@pytest.mark.parametrize(
    ("expected_game", "actual_game"),
    tuple((expected, actual) for expected in GAMES for actual in GAMES if expected != actual),
)
def test_profile_detects_every_wrong_supported_game_pair(
    tmp_path: Path, expected_game: str, actual_game: str
) -> None:
    store, directory = _installation(tmp_path, actual_game)

    profile = store.inspect(expected_game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "wrong_game"
    assert profile.issue.detected_game is not None
    assert profile.issue.detected_game.key == actual_game
    assert pal.paths[expected_game] in profile.missing_files


@pytest.mark.parametrize("game", GAMES)
def test_profile_distinguishes_missing_expected_palette(tmp_path: Path, game: str) -> None:
    store, directory = _installation(tmp_path, game)
    (directory / pal.paths[game]).unlink()

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_palette"
    assert profile.issue.paths == (pal.paths[game],)


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("resource", ("palette", "tileflag"))
def test_profile_reports_case_mismatched_game_filename(
    tmp_path: Path, game: str, resource: str
) -> None:
    store, directory = _installation(tmp_path, game)
    expected_name = pal.paths[game] if resource == "palette" else resource
    actual_name = expected_name.upper()
    (directory / expected_name).rename(directory / actual_name)

    profile = store.inspect(game, directory)

    if (directory / expected_name).is_file():
        assert profile.issue is None
        assert profile.ready
        return

    assert profile.issue is not None
    assert profile.issue.kind.value == "case_mismatch"
    assert expected_name in profile.issue.paths
    assert actual_name in profile.issue.paths


@pytest.mark.parametrize("game", GAMES)
def test_profile_distinguishes_missing_core_data(tmp_path: Path, game: str) -> None:
    store, directory = _installation(tmp_path, game)
    (directory / "tileflag").unlink()

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_core_files"
    assert profile.issue.paths == ("tileflag",)


@pytest.mark.parametrize("game", GAMES)
def test_profile_distinguishes_missing_save_directory(tmp_path: Path, game: str) -> None:
    store, directory = _installation(tmp_path, game)
    shutil.rmtree(directory / "savegame")

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_save_directory"
    assert len(profile.missing_files) == 70
    assert "savegame/objlist" in profile.missing_files


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("remove_all_blocks", (False, True))
def test_profile_groups_missing_save_index_and_object_blocks(
    tmp_path: Path, game: str, remove_all_blocks: bool
) -> None:
    store, directory = _installation(tmp_path, game)
    savegame = directory / "savegame"
    (savegame / "objlist").unlink()
    for block in savegame.glob("objblk*" if remove_all_blocks else "objblkaa"):
        block.unlink()

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_save_files"
    assert len(profile.missing_files) == (70 if remove_all_blocks else 2)
    assert "savegame/objlist" in profile.issue.paths
    assert "object block" in profile.issue.details
    assert "69" in profile.issue.details if remove_all_blocks else "objblkaa" in profile.issue.details


@pytest.mark.parametrize("game", GAMES)
def test_profile_preserves_mixed_core_and_save_omissions(tmp_path: Path, game: str) -> None:
    store, directory = _installation(tmp_path, game)
    (directory / "tileflag").unlink()
    (directory / "savegame" / "objblkaa").unlink()

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_core_files"
    assert profile.missing_files == ("savegame/objblkaa", "tileflag")
    assert profile.issue.paths == profile.missing_files


@pytest.mark.parametrize("game", GAMES)
def test_profile_avoids_confident_wrong_game_for_ambiguous_palettes(
    tmp_path: Path, game: str
) -> None:
    store, directory = _installation(tmp_path, game)
    (directory / pal.paths[game]).unlink()
    for other in GAMES:
        if other != game:
            (directory / pal.paths[other]).write_bytes(b"palette signature")

    profile = store.inspect(game, directory)

    assert profile.issue is not None
    assert profile.issue.kind.value == "missing_palette"
    assert profile.issue.detected_game is None


@pytest.mark.parametrize("game", GAMES)
def test_profile_preserves_legacy_constructor_and_ready_installation(
    tmp_path: Path, game: str
) -> None:
    store, directory = _installation(tmp_path, game)

    inspected = store.inspect(game, directory)
    legacy = GameProfile(inspected.specification, directory, ())

    assert inspected.issue is None
    assert inspected.ready
    assert legacy.issue is None
    assert legacy.ready
