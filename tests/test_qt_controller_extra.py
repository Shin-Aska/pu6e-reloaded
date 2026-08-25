from __future__ import annotations

import pytest

from U6 import Map, NPCs, obj


def test_save_propagates_object_writer_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from pu6e_qt.controller import EditorController

    calls: list[str] = []

    def fail_objects() -> None:
        calls.append("objects")
        raise OSError("disk full")

    monkeypatch.setattr(obj, "write_changes", fail_objects)
    monkeypatch.setattr(NPCs, "write", lambda: calls.append("npcs"))
    monkeypatch.setattr(Map, "write_changes", lambda: calls.append("map"))

    with pytest.raises(OSError, match="disk full"):
        EditorController().save()

    assert calls == ["objects"]
