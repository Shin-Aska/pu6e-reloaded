"""Structured errors raised at binary format boundaries."""

from typing import override


class FormatError(ValueError):
    """A malformed resource, with its location and the violated wire constraint."""

    def __init__(self, resource: str, detail: str, offset: int | None = None) -> None:
        self.resource: str = resource
        self.detail: str = detail
        self.offset: int | None = offset
        super().__init__(str(self))

    @override
    def __str__(self) -> str:
        location = "" if self.offset is None else f" at offset {self.offset:#x}"
        return f"{self.resource}{location}: {self.detail}"
