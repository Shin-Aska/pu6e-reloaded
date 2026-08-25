from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QFormLayout, QLineEdit, QSpinBox, QWidget

from U6.obj import Obj

from .object_tree import ObjectStack

if TYPE_CHECKING:
    from .controller import EditorController

__all__ = ["ObjectInspector", "ObjectStack"]


class ObjectInspector(QWidget):
    object_changed = Signal(Obj)

    def __init__(self, controller: EditorController) -> None:
        super().__init__()
        self.controller = controller
        self.current_object: Obj | None = None
        self.type = QSpinBox(self)
        self.type.setRange(0, 0x3FF)
        self.frame = QSpinBox(self)
        self.quantity = QSpinBox(self)
        self.quantity.setRange(0, 0xFF)
        self.quality = QSpinBox(self)
        self.quality.setRange(0, 0xFF)
        self.status = QSpinBox(self)
        self.status.setRange(0, 0xFF)
        self.status.setDisplayIntegerBase(16)
        self.weight = QLineEdit(self)
        self.weight.setReadOnly(True)

        layout = QFormLayout(self)
        for label, field in (
            ("&Type", self.type),
            ("&Frame", self.frame),
            ("&Quantity", self.quantity),
            ("Q&uality", self.quality),
            ("&Status", self.status),
            ("&Weight", self.weight),
        ):
            field.setAccessibleName(label.replace("&", ""))
            layout.addRow(label, field)

        self.type.valueChanged.connect(self._type_changed)
        self.frame.valueChanged.connect(self._frame_changed)
        self.quantity.valueChanged.connect(self._quantity_changed)
        self.quality.valueChanged.connect(self._quality_changed)
        self.status.valueChanged.connect(self._status_changed)
        self.set_object(None)

    def set_object(self, selected: Obj | None) -> None:
        self.current_object = selected
        blockers = [
            QSignalBlocker(field)
            for field in (self.type, self.frame, self.quantity, self.quality, self.status)
        ]
        for field in (self.type, self.frame, self.quantity, self.quality, self.status):
            field.setEnabled(selected is not None)
        if selected is None:
            self.type.setValue(0)
            self.frame.setRange(0, 0)
            self.quantity.setValue(0)
            self.quality.setValue(0)
            self.status.setValue(0)
            self.weight.clear()
        else:
            self.type.setValue(selected.basetype())
            self.frame.setRange(0, max(0, selected.num_frames() - 1))
            self.frame.setValue(selected.frame())
            self.quantity.setValue(selected.quantity)
            self.quality.setValue(selected.quality)
            self.status.setValue(selected.status)
            self.weight.setText(f"{selected.weight_total() / 10:g} stones")
        del blockers

    def _update_property(self, name: str, value: int) -> None:
        selected = self.current_object
        if selected is None:
            return
        self.controller.update_object_property(selected, name, value)
        self.weight.setText(f"{selected.weight_total() / 10:g} stones")
        self.object_changed.emit(selected)

    def _type_changed(self, value: int) -> None:
        selected = self.current_object
        if selected is None:
            return
        previous_frame = self.frame.value()
        selected.set_type(value)
        blocker = QSignalBlocker(self.frame)
        self.frame.setRange(0, max(0, selected.num_frames() - 1))
        self.frame.setValue(min(previous_frame, self.frame.maximum()))
        selected.set_frame(self.frame.value())
        del blocker
        self.controller.mark_object_changed(selected)
        self.weight.setText(f"{selected.weight_total() / 10:g} stones")
        self.object_changed.emit(selected)

    def _frame_changed(self, value: int) -> None:
        self._update_property("frame", value)

    def _quantity_changed(self, value: int) -> None:
        self._update_property("quantity", value)

    def _quality_changed(self, value: int) -> None:
        self._update_property("quality", value)

    def _status_changed(self, value: int) -> None:
        self._update_property("status", value)
