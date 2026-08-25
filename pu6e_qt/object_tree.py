from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
    QVBoxLayout,
    QWidget,
)

from U6 import obj
from U6.Point import Point
from U6.obj import Obj

if TYPE_CHECKING:
    from .controller import EditorController


class ObjectStack(QWidget):
    object_selected = Signal(Obj)

    def __init__(self, controller: EditorController) -> None:
        super().__init__()
        self.controller = controller
        self.point: Point | None = None
        self.coordinates = (0, 0, 0)
        self.clipboard: Obj | None = None
        self.default_object: Obj | None = None
        self._items: dict[int, Obj] = {}
        self.position = QLabel("No location selected", self)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Objects at selected map location")
        self.tree.currentItemChanged.connect(self._selection_changed)
        self.clipboard_label = QLabel("Clipboard: empty", self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.position)
        layout.addWidget(self.tree)
        layout.addWidget(self.clipboard_label)
        bindings: tuple[tuple[str, Callable[[], None]], ...] = (
            ("X", self.cut_selected),
            ("C", self.copy_selected),
            ("V", self.paste_after),
            ("Shift+V", self.paste_before),
            ("B", self.paste_into),
            ("Ctrl+V", self.paste_into),
            ("N", self.create_default),
            ("Insert", self.create_default),
            ("Delete", self.delete_selected),
        )
        self._bindings = {
            QKeySequence(sequence).toString(): handler for sequence, handler in bindings
        }
        self.tree.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.tree and isinstance(event, QKeyEvent):
            handler = self._bindings.get(QKeySequence(event.keyCombination()).toString())
            if handler is not None:
                if event.type() == QEvent.Type.ShortcutOverride:
                    event.accept()
                    return True
                if event.type() == QEvent.Type.KeyPress:
                    handler()
                    event.accept()
                    return True
        return super().eventFilter(watched, event)

    def set_point(self, point: Point | None, x: int, y: int, z: int) -> None:
        self.point = point
        self.coordinates = x, y, z
        self.position.setText(f"Position: {x:03x}, {y:03x}, {z:x}")
        self._rebuild()

    def set_default_obj(self, default: Obj) -> None:
        self.default_object = default

    def _rebuild(self, selected: Obj | None = None) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        self._items.clear()
        if self.point is not None:
            self._append_children(self.tree.invisibleRootItem(), self.point)
        self.tree.blockSignals(False)
        current = self._item_for(selected) if selected is not None else None
        if current is None and self.tree.topLevelItemCount():
            current = self.tree.topLevelItem(self.tree.topLevelItemCount() - 1)
        if current is None:
            self.controller.select_object(None)
        else:
            self.tree.setCurrentItem(current)

    def _append_children(self, parent: QTreeWidgetItem, children: Iterable[Obj]) -> None:
        for child in children:
            item = QTreeWidgetItem(parent, [child.name()])
            self._items[id(item)] = child
            self._append_children(item, child.contains)
            if child.contains:
                item.setExpanded(True)

    def _item_for(self, selected: Obj) -> QTreeWidgetItem | None:
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value() is not None:
            current = iterator.value()
            if current is not None and self._items.get(id(current)) is selected:
                return current
            iterator += 1
        return None

    def _selection_changed(self, current: QTreeWidgetItem | None) -> None:
        selected = self._items.get(id(current)) if current is not None else None
        self.controller.select_object(selected)
        if selected is not None:
            self.object_selected.emit(selected)

    def _current(self) -> Obj | None:
        item = self.tree.currentItem()
        return self._items.get(id(item)) if item is not None else None

    def _parent_and_index(self, item: QTreeWidgetItem) -> tuple[Point | Obj, int] | None:
        selected = self._items.get(id(item))
        if selected is None:
            return None
        parent_item = item.parent()
        container = self.point if parent_item is None else self._items.get(id(parent_item))
        if container is None:
            return None
        for index, candidate in enumerate(container):
            if candidate is selected:
                return container, index
        return None

    def _set_clipboard(self, selected: Obj | None) -> None:
        self.clipboard = selected
        description = selected.name() if selected is not None else "empty"
        self.clipboard_label.setText(f"Clipboard: {description}")

    def _changed(self, selected: Obj | None = None) -> None:
        self.controller.mark_dirty(*self.coordinates)
        self._rebuild(selected)

    def delete_selected(self) -> None:
        item = self.tree.currentItem()
        location = self._parent_and_index(item) if item is not None else None
        if location is None:
            return
        parent, index = location
        del parent[index]
        self._changed()

    def cut_selected(self) -> None:
        item = self.tree.currentItem()
        location = self._parent_and_index(item) if item is not None else None
        if location is None:
            return
        parent, index = location
        selected = self._items[id(item)]
        del parent[index]
        self._set_clipboard(selected)
        self._changed()

    def copy_selected(self) -> None:
        selected = self._current()
        if selected is None:
            return
        cloned: Obj | None = selected.clone()
        if cloned is not None:
            self._set_clipboard(cloned)

    def create_default(self) -> None:
        template = self.default_object if self.default_object is not None else obj.default_object()
        cloned: Obj | None = template.clone()
        if cloned is not None:
            self._set_clipboard(cloned)

    def paste_before(self) -> None:
        self._paste_sibling(before=True)

    def paste_after(self) -> None:
        self._paste_sibling(before=False)

    def _paste_sibling(self, *, before: bool) -> None:
        clipboard = self.clipboard
        if clipboard is None:
            return
        item = self.tree.currentItem()
        location = self._parent_and_index(item) if item is not None else None
        if location is None:
            if self.point is None:
                self.point = obj.add_point_at(*self.coordinates)
            parent, index = self.point, len(self.point)
        else:
            parent, index = location
            index += int(not before)
        parent.insert(index, clipboard)
        self._set_clipboard(None)
        self._changed(clipboard)

    def paste_into(self) -> None:
        selected = self._current()
        clipboard = self.clipboard
        if selected is None or clipboard is None:
            return
        if clipboard is selected or self._contains(clipboard, selected):
            return
        selected.insert(len(selected.contains), clipboard)
        self._set_clipboard(None)
        self._changed(clipboard)

    def move_object(self, source: Obj, destination: Obj) -> bool:
        if source is destination or self._contains(source, destination):
            return False
        source_item = self._item_for(source)
        location = self._parent_and_index(source_item) if source_item is not None else None
        if location is None:
            return False
        parent, index = location
        del parent[index]
        destination.insert(len(destination.contains), source)
        self._changed(source)
        return True

    def _contains(self, parent: Obj, target: Obj) -> bool:
        return any(child is target or self._contains(child, target) for child in parent.contains)
