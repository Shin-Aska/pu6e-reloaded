from __future__ import annotations

from pathlib import Path
from struct import pack

import pytest

from pu6e_qt.conversations import read_conversations
from pu6e_qt.controller import EditorController
from pu6e_qt.game_profiles import GameProfileStore
from test_core import write_game_fixture
from U6 import Config, Font, Map, NPCs, obj


GAMES = ("fp", "md", "se")


def _case_variant_installation(tmp_path: Path, game: str, mixed_case: bool) -> Path:
    directory = tmp_path / game
    write_game_fixture(directory, game, game)
    (directory / "u6.ch").write_bytes(bytes(2048))
    payload = b"\xff\x02Dupre\xf1Search for the shrine."
    (directory / "converse.a").write_bytes(pack("<II", 0, 8) + bytes(4) + payload)

    for entry in sorted(directory.rglob("*"), key=lambda path: len(path.parts), reverse=True):
        name = entry.name.title() if mixed_case else entry.name.upper()
        entry.rename(entry.with_name(name))

    return directory


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("mixed_case", (False, True), ids=("uppercase", "mixed-case"))
def test_launcher_accepts_case_insensitive_dos_installations(
    tmp_path: Path, game: str, mixed_case: bool
) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case)

    profile = GameProfileStore(tmp_path / "config.ini").inspect(game, directory)

    assert profile.issue is None
    assert profile.missing_files == ()
    assert profile.ready


@pytest.mark.parametrize("game", GAMES)
@pytest.mark.parametrize("mixed_case", (False, True), ids=("uppercase", "mixed-case"))
def test_editor_loads_case_insensitive_dos_resources_and_saved_games(
    tmp_path: Path, game: str, mixed_case: bool
) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case)

    controller = EditorController()
    controller.load_game(directory, game)

    assert Config.gametype == game
    assert len(Map.map) == 69
    assert len(obj.objblk) == 69
    assert len(NPCs.npcs) == 256
    assert Font.chardata is not None
    assert [(item.npc_id, item.name) for item in read_conversations(directory)] == [(2, "Dupre")]


@pytest.mark.parametrize("game", GAMES)
def test_editor_saves_to_existing_uppercase_dos_game_files(tmp_path: Path, game: str) -> None:
    directory = _case_variant_installation(tmp_path, game, mixed_case=False)
    controller = EditorController()
    controller.load_game(directory, game)
    controller.paint_tile(1, 0, 0, 0)
    controller.mark_dirty(0, 0, 0)

    controller.save()

    assert Map.maptile_at(0, 0, 0) == 1
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
