"""Read conversation archives from a game installation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from game.format.conversations import decode_conversation_archive
from game.format.resources import resolve_dos_path

if TYPE_CHECKING:
    from pathlib import Path

    from game.models.conversations import Conversation

_ARCHIVES: Final = ("converse.a", "converse.b")


def read_conversations(directory: Path) -> tuple[Conversation, ...]:
    """Read conversations from every available archive in an installation."""
    conversations: list[Conversation] = []
    for archive in _ARCHIVES:
        path = resolve_dos_path(directory / archive)
        if not path.is_file():
            continue

        conversations.extend(decode_conversation_archive(path.read_bytes(), archive))
    return tuple(conversations)
