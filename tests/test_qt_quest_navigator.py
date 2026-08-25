from __future__ import annotations

from pathlib import Path
from struct import pack

import pytest
from PySide6.QtWidgets import QApplication

from test_core import encode_lzw_literals, write_game_fixture
from U6 import NPCs
from pu6e_qt.controller import EditorController


@pytest.fixture(scope="session")
def quest_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _conversation_archive(npc_id: int, name: str, dialogue: str) -> bytes:
    payload = bytes((0xFF, npc_id)) + name.encode() + b"\xf1" + dialogue.encode()
    compressed = encode_lzw_literals(payload)
    return pack("<II", 0, 8) + compressed


def test_conversation_reader_extracts_named_npcs_and_searchable_dialogue(tmp_path: Path) -> None:
    from pu6e_qt.conversations import read_conversations

    (tmp_path / "converse.a").write_bytes(
        _conversation_archive(2, "Dupre", '"The quest begins at the shrine."')
    )

    conversations = read_conversations(tmp_path)

    assert len(conversations) == 1
    assert conversations[0].npc_id == 2
    assert conversations[0].name == "Dupre"
    assert "quest begins at the shrine" in conversations[0].dialogue


def test_conversation_reader_supports_uncompressed_archive_entries(tmp_path: Path) -> None:
    from pu6e_qt.conversations import read_conversations

    payload = b"\xff\x05Lord British\xf1Ask about the gargoyles."
    (tmp_path / "converse.b").write_bytes(pack("<II", 0, 8) + bytes(4) + payload)

    conversations = read_conversations(tmp_path)

    assert [(entry.npc_id, entry.name) for entry in conversations] == [(5, "Lord British")]


def test_quest_navigator_searches_dialogue_and_jumps_to_npc(
    tmp_path: Path,
    quest_app: QApplication,
) -> None:
    from pu6e_qt.quest_navigator import QuestNavigator

    game_directory = tmp_path / "quests"
    write_game_fixture(game_directory, "fp", "quest navigator")
    (game_directory / "converse.a").write_bytes(
        _conversation_archive(2, "Dupre", '"Bring the lens to the shrine."')
    )
    controller = EditorController()
    controller.load_game(game_directory, "fp")
    npc = NPCs.npcs[2]
    npc.type = 1
    npc.x, npc.y, npc.z = 0x120, 0x160, 0
    navigator = QuestNavigator(controller)

    navigator.search.setText("lens")
    navigator.entries.setCurrentRow(0)
    navigator.jump.click()

    assert navigator.entries.count() == 1
    assert "shrine" in navigator.preview.toPlainText()
    assert navigator.preview.isReadOnly()
    assert controller.position == (0x120, 0x160, 0)


def test_quest_navigator_activation_cannot_jump_to_an_unavailable_npc(
    tmp_path: Path,
    quest_app: QApplication,
) -> None:
    from pu6e_qt.quest_navigator import QuestNavigator

    game_directory = tmp_path / "unavailable-npc"
    write_game_fixture(game_directory, "fp", "unavailable npc")
    (game_directory / "converse.a").write_bytes(
        _conversation_archive(2, "Dupre", '"An unavailable character."')
    )
    controller = EditorController()
    controller.load_game(game_directory, "fp")
    controller.set_position(0x134, 0x16C, 0)
    npc = NPCs.npcs[2]
    npc.type = 0
    npc.x, npc.y, npc.z = 0x080, 0x090, 7
    navigator = QuestNavigator(controller)
    navigator.entries.setCurrentRow(0)
    selected = navigator.entries.currentItem()
    assert selected is not None
    original_position = controller.position

    navigator.entries.itemActivated.emit(selected)

    assert not navigator.jump.isEnabled()
    assert controller.position == original_position


def test_quest_navigator_explains_when_conversation_archives_are_unavailable(
    tmp_path: Path,
    quest_app: QApplication,
) -> None:
    from pu6e_qt.quest_navigator import QuestNavigator

    game_directory = tmp_path / "no-conversations"
    write_game_fixture(game_directory, "md", "martian dreams")
    controller = EditorController()
    controller.load_game(game_directory, "md")

    navigator = QuestNavigator(controller)

    assert navigator.entries.count() == 0
    assert "not available" in navigator.preview.toPlainText().lower()
    assert not navigator.jump.isEnabled()
