"""A loaded world and the editor bound to its mutable state."""

from typing import TYPE_CHECKING

from game.services.editor import WorldEditor

if TYPE_CHECKING:
    from game.models.world import WorldState


class WorldSession:
    """Keep a loaded state and its editor together throughout a document's lifetime."""

    def __init__(self, state: WorldState) -> None:
        self.state: WorldState = state
        self.editor: WorldEditor = WorldEditor(state)
