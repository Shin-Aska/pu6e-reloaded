from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pu6e_qt.controller import EditorController
from pu6e_qt.conversations import Conversation, read_conversations
from pu6e_qt.icons import action_icon


class QuestNavigator(QWidget):
    def __init__(self, controller: EditorController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self._conversations: tuple[Conversation, ...] = ()

        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search character, clue, or dialogue")
        self.search.setAccessibleName("Search NPC conversations and quest clues")

        self.entries = QListWidget(self)
        self.entries.setAccessibleName("Characters and conversation scripts")

        self.preview = QPlainTextEdit(self)
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Read-only extracted conversation text")

        self.jump = QPushButton(action_icon("locate"), "Jump to character", self)
        self.jump.setAccessibleName("Jump to the selected character's world location")
        self.jump.setEnabled(False)

        self.notice = QLabel("Dialogue is read-only; quest scripting is not decoded.", self)
        self.notice.setWordWrap(True)
        self.notice.setObjectName("quest-authoring-notice")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self.search)
        layout.addWidget(self.entries, 3)
        layout.addWidget(self.preview, 4)
        layout.addWidget(self.jump)
        layout.addWidget(self.notice)

        self.search.textChanged.connect(self._filter)
        self.entries.currentItemChanged.connect(self._show_conversation)
        self.entries.itemActivated.connect(self._jump_to_character)
        self.jump.clicked.connect(self._jump_to_character)
        controller.session_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self._conversations = (
            read_conversations(self.controller.session.state.game_dir)
            if self.controller.is_loaded
            else ()
        )
        self._filter(self.search.text())

    def _filter(self, query: str) -> None:
        self.entries.clear()
        needle = query.casefold()
        for conversation in self._conversations:
            searchable = f"{conversation.name} {conversation.dialogue}".casefold()
            if needle and needle not in searchable:
                continue
            item = QListWidgetItem(f"{conversation.npc_id:03}  {conversation.name}")
            item.setData(Qt.ItemDataRole.UserRole, conversation.npc_id)
            self.entries.addItem(item)

        if self.entries.count():
            self.entries.setCurrentRow(0)
        else:
            message = (
                "No matching character or dialogue was found."
                if self._conversations
                else "Conversation archives are not available for this game."
            )
            self.preview.setPlainText(message)
            self.jump.setEnabled(False)

    def _show_conversation(self, current: QListWidgetItem | None) -> None:
        if current is None:
            self.jump.setEnabled(False)
            return
        npc_id = current.data(Qt.ItemDataRole.UserRole)
        conversation = next(entry for entry in self._conversations if entry.npc_id == npc_id)
        self.preview.setPlainText(conversation.dialogue)
        npc = self.controller.session.state.npcs[npc_id]
        self.jump.setEnabled(bool(npc.packed_type) and 0 <= npc.z <= 5)

    def _jump_to_character(self) -> None:
        current = self.entries.currentItem()
        if current is None:
            return
        npc = self.controller.session.state.npcs[current.data(Qt.ItemDataRole.UserRole)]
        if not npc.packed_type or not 0 <= npc.z <= 5:
            return
        self.controller.set_position(npc.x, npc.y, npc.z)
