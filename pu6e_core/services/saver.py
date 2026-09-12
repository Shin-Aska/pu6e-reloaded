"""Persist dirty world data with exact backups and per-file atomic replacement."""

from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

from pu6e_core.formats.npcs import encode_objlist
from pu6e_core.formats.objects import encode_object_block
from pu6e_core.formats.resources import OBJECT_BLOCK_FILES, resolve_dos_path
from pu6e_core.formats.terrain import encode_chunks, encode_map

if TYPE_CHECKING:
    from pu6e_core.services.session import WorldSession


@dataclass(frozen=True, slots=True)
class SaveResult:
    """Successfully written targets and their original-content backups in order."""

    touched: tuple[Path, ...]
    backups: tuple[Path, ...]


def _atomic_write(path: Path, data: bytes) -> None:
    """Replace a single file only after its temporary file is fully written."""
    temporary: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as output:
            temporary = Path(output.name)
            _ = output.write(data)
        _ = temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _write_with_backup(path: Path, data: bytes) -> tuple[Path, Path]:
    target = resolve_dos_path(path)
    backup = resolve_dos_path(target.with_name(f"{target.name}.bak"))
    _atomic_write(backup, target.read_bytes())
    _atomic_write(target, data)
    return target, backup


class WorldSaver:
    """Clear only dirtiness whose corresponding file was successfully written."""

    @staticmethod
    def save(session: WorldSession) -> SaveResult:
        """Write objects, NPCs, and terrain, propagating any disk failure."""
        state = session.state
        touched: list[Path] = []
        backups: list[Path] = []

        def write(filename: str, data: bytes) -> None:
            target, backup = _write_with_backup(state.game_dir / filename, data)
            touched.append(target)
            backups.append(backup)

        for block in sorted(state.dirty_object_blocks):
            write(
                OBJECT_BLOCK_FILES[block],
                encode_object_block(state.object_blocks[block]),
            )
            state.dirty_object_blocks.remove(block)

        write(
            "savegame/objlist",
            encode_objlist(state.npcs, state.objlist_prefix, state.objlist_trailer),
        )
        if state.terrain.chunks_dirty:
            write("chunks", encode_chunks(state.terrain.chunks))
            state.terrain.chunks_dirty = False
        if state.terrain.map_dirty:
            write("map", encode_map(state.terrain.superchunks))
            state.terrain.map_dirty = False
        return SaveResult(tuple(touched), tuple(backups))
