from __future__ import annotations

from pathlib import Path


def resolve_dos_path(path: Path | str) -> Path:
    requested = Path(path)
    if requested.exists():
        return requested

    if requested.is_absolute():
        current = Path(requested.anchor)
        components = requested.parts[1:]
    else:
        current = Path.cwd()
        components = requested.parts

    for component in components:
        candidate = current / component
        if candidate.exists() or not current.is_dir():
            current = candidate
            continue

        current = next(
            (entry for entry in current.iterdir() if entry.name.casefold() == component.casefold()),
            candidate,
        )

    return current
