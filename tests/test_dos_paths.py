from __future__ import annotations

from struct import pack
from typing import TYPE_CHECKING, Final

import pytest

from game.models.game import GameType
from game.services.conversations import read_conversations
from game.services.loader import WorldLoader
from game.services.saver import WorldSaver
from game_fixtures import write_game_fixture
from ui.profile.store import GameProfileStore
from ui.settings.store import SettingsStore

if TYPE_CHECKING:
    from pathlib import Path


GAMES: Final = ("fp", "md", "se")


def _case_variant_installation(tmp_path: Path, game: str, mixed_case: bool) -> Path:
    directory = tmp_path / game
    write_game_fixture(directory, game, game)
    _ = (directory / "u6.ch").write_bytes(bytes(2048))
    payload = b"\xff\x02Dupre\xf1Search for the shrine."
    _ = (directory / "converse.a").write_bytes(pack("<II", 0, 8) + bytes(4) + payload)

    for entry in sorted(directory.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        name = entry.name.title() if mixed_case else entry.name.upper()
        _ = entry.rename(entry.with_name(name))

    return directory


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("mixed_case", [False, True], ids=("uppercase", "mixed-case"))
def test_launcher_accepts_case_insensitive_dos_installations(
    tmp_path: Path, game: str, mixed_case: bool
) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case)

    profile = GameProfileStore(SettingsStore(tmp_path / "config.ini")).inspect(game, directory)

    assert profile.issue is None
    assert profile.missing_files == ()
    assert profile.ready


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("mixed_case", [False, True], ids=("uppercase", "mixed-case"))
def test_editor_loads_case_insensitive_dos_resources_and_saved_games(
    tmp_path: Path, game: str, mixed_case: bool
) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case)

    state = WorldLoader.load(directory, game).state

    assert state.game_type == GameType(game)
    assert len(state.terrain.superchunks) == 69
    assert len(state.object_blocks) == 69
    assert len(state.npcs) == 256
    assert state.assets.font is not None
    assert [(item.npc_id, item.name) for item in read_conversations(directory)] == [(2, "Dupre")]


@pytest.mark.parametrize("game", GAMES)
def test_editor_saves_to_existing_uppercase_dos_game_files(tmp_path: Path, game: str) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case=False)
    session = WorldLoader.load(directory, game)
    session.editor.set_map_tile(1, 0, 0, 0)
    session.editor.mark_object_changed(0, 0, 0)

    _ = WorldSaver.save(session)

    assert session.editor.map_tile_at(0, 0, 0) == 1
    assert (directory / "CHUNKS").read_bytes()[0] == 1
    assert (directory / "CHUNKS.bak").is_file()
    assert (directory / "SAVEGAME" / "OBJBLKAA.bak").is_file()
    assert (directory / "SAVEGAME" / "OBJLIST.bak").is_file()
    assert [path.name for path in directory.iterdir() if path.name.casefold() == "chunks"] == [
        "CHUNKS"
    ]
    assert [path.name for path in directory.iterdir() if path.name.casefold() == "savegame"] == [
        "SAVEGAME"
    ]
