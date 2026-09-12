"""Immutable conversation records decoded from Ultima VI archives."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Conversation:
    """The searchable dialogue spoken by one NPC in one archive."""

    npc_id: int
    name: str
    dialogue: str
    archive: str
