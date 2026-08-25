from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from struct import unpack_from
from typing import Final

from U6 import dospath, lzw


_ARCHIVES: Final = ("converse.a", "converse.b")
_DIALOGUE_TEXT: Final = re.compile(rb"[\x20-\x7e\r\n]{4,}")


@dataclass(frozen=True, slots=True)
class Conversation:
    npc_id: int
    name: str
    dialogue: str
    archive: str


def read_conversations(directory: Path) -> tuple[Conversation, ...]:
    conversations: list[Conversation] = []
    for archive in _ARCHIVES:
        path = dospath.resolve_dos_path(directory / archive)
        if not path.is_file():
            continue

        data = path.read_bytes()
        first_offset = next(
            offset
            for index in range(0, min(len(data), 16), 4)
            if (offset := unpack_from("<I", data, index)[0])
        )
        offsets = unpack_from(f"<{first_offset // 4}I", data)
        for index, offset in enumerate(offsets):
            if not offset:
                continue
            end = next((value for value in offsets[index + 1 :] if value), len(data))
            entry = data[offset:end]
            payload = (
                lzw.decompress_buffer(entry)
                if lzw.is_valid_lzw_buffer(entry)
                else entry[4:]
            )
            npc_id = payload[1]
            name, _, dialogue = payload[2:].partition(b"\xf1")
            lines = (
                segment.decode("cp437").strip()
                for segment in _DIALOGUE_TEXT.findall(dialogue)
            )
            conversations.append(
                Conversation(
                    npc_id=npc_id,
                    name=name.decode("cp437"),
                    dialogue="\n".join(line for line in lines if line),
                    archive=archive,
                )
            )
    return tuple(conversations)
