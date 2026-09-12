from __future__ import annotations

from struct import pack
from typing import TYPE_CHECKING

import pytest

from game.format.conversations import decode_conversation_archive
from game.format.errors import FormatError
from game.models.conversations import Conversation
from game.services.conversations import read_conversations
from tests.game_fixtures import encode_lzw_literals

if TYPE_CHECKING:
    from pathlib import Path


def _archive(entry: bytes) -> bytes:
    return pack("<II", 0, 8) + entry


def test_decode_conversation_archive_preserves_compressed_cp437_dialogue() -> None:
    payload = b"\xff\x02Caf\x82\xf1Search for the shrine."

    conversations = decode_conversation_archive(
        _archive(encode_lzw_literals(payload)), "converse.a"
    )

    assert conversations == (
        Conversation(2, "Caf\u00e9", "Search for the shrine.", "converse.a"),
    )


def test_read_conversations_reads_raw_case_variant_archive_and_skips_missing_archive(
    tmp_path: Path,
) -> None:
    raw_payload = b"\xff\x05Lord British\xf1Ask about the gargoyles."
    _ = (tmp_path / "CONVERSE.B").write_bytes(_archive(bytes(4) + raw_payload))

    conversations = read_conversations(tmp_path)

    assert [(item.npc_id, item.name, item.archive) for item in conversations] == [
        (5, "Lord British", "converse.b")
    ]


@pytest.mark.parametrize(
    "data",
    [
        b"",
        pack("<I", 8),
        _archive(bytes(4)),
    ],
)
def test_decode_conversation_archive_rejects_malformed_binary_input(data: bytes) -> None:
    with pytest.raises(FormatError):
        _ = decode_conversation_archive(data, "converse.a")
