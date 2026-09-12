"""Decode the binary conversation archives shipped with Ultima VI games."""

import re
from typing import Final

from game.format.errors import FormatError
from game.format.lzw import decompress_buffer, is_valid_lzw_buffer
from game.models.conversations import Conversation

_OFFSET_SCAN_BYTES: Final = 16
_DIALOGUE_TEXT: Final = re.compile(rb"[\x20-\x7e\r\n]{4,}")


def _decode_offsets(data: bytes, archive: str) -> tuple[int, ...]:
    scan_limit = min(len(data), _OFFSET_SCAN_BYTES)
    scan_limit -= scan_limit % 4
    first_offset = 0
    first_index = 0
    for index in range(0, scan_limit, 4):
        offset = int.from_bytes(data[index : index + 4], "little")
        if offset:
            first_offset = offset
            first_index = index
            break
    if not first_offset:
        raise FormatError(archive, "missing conversation offset table")
    if first_offset % 4 or first_offset > len(data) or first_offset < first_index + 4:
        raise FormatError(archive, "invalid conversation offset table", first_index)
    return tuple(
        int.from_bytes(data[index : index + 4], "little")
        for index in range(0, first_offset, 4)
    )


def _conversation_payload(entry: bytes, archive: str, offset: int) -> bytes:
    payload = decompress_buffer(entry) if is_valid_lzw_buffer(entry) else entry[4:]
    if len(payload) < 2:
        raise FormatError(archive, "truncated conversation payload", offset)
    return payload


def decode_conversation_archive(data: bytes, archive: str) -> tuple[Conversation, ...]:
    """Decode one raw or LZW-compressed conversation archive into records."""
    offsets = _decode_offsets(data, archive)
    conversations: list[Conversation] = []
    for index, offset in enumerate(offsets):
        if not offset:
            continue
        end = next((value for value in offsets[index + 1 :] if value), len(data))
        if offset < len(offsets) * 4 or offset >= len(data) or end <= offset or end > len(data):
            raise FormatError(archive, "invalid conversation entry offset", offset)
        payload = _conversation_payload(data[offset:end], archive, offset)
        separator = payload.find(b"\xf1", 2)
        if separator < 0:
            raise FormatError(archive, "missing conversation dialogue separator", offset)
        segments: list[bytes] = _DIALOGUE_TEXT.findall(payload[separator + 1 :])
        dialogue = "\n".join(
            line for segment in segments if (line := segment.decode("cp437").strip())
        )
        conversations.append(
            Conversation(
                npc_id=payload[1],
                name=payload[2:separator].decode("cp437"),
                dialogue=dialogue,
                archive=archive,
            )
        )
    return tuple(conversations)
