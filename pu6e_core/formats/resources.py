"""Explicit installation manifests and DOS-era resource file decoding."""

from dataclasses import dataclass
from enum import IntFlag
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from pu6e_core.formats.errors import FormatError
from pu6e_core.formats.lzw import decompress_buffer
from pu6e_core.models.game import GameType

if TYPE_CHECKING:
    from collections.abc import Mapping


class ResourceEncoding(IntFlag):
    """Independent transformations applied to a resource's stored bytes."""

    RAW = 0
    LZW = 1
    LIBHDR = 2
    EMPTY = 4


@dataclass(frozen=True, slots=True)
class ResourceSpec:
    """An installation-relative filename and its decoding requirements."""

    filename: str
    encoding: ResourceEncoding = ResourceEncoding.RAW
    required: bool = True


@dataclass(frozen=True, slots=True)
class GameManifest:
    """The immutable resource inventory for one supported game."""

    game: GameType
    palette_name: str
    resources: Mapping[str, ResourceSpec]

    def __post_init__(self) -> None:
        """Detach resource definitions from the manifest builder's mapping."""
        object.__setattr__(self, "resources", MappingProxyType(dict(self.resources)))

    @property
    def required_files(self) -> tuple[str, ...]:
        """List all files required to load this game, including saved objects."""
        return tuple(
            sorted(
                {
                    spec.filename
                    for spec in self.resources.values()
                    if spec.required and not spec.encoding & ResourceEncoding.EMPTY
                }
            )
        )


OBJECT_BLOCK_FILES: Final = tuple(
    f"savegame/objblk{x}{y}" for y in "abcdefgh" for x in "abcdefgh"
) + tuple(f"savegame/objblk{x}i" for x in "abcde")


def _manifest(game: GameType, palette: str, *, compressed: bool) -> GameManifest:
    encoding = ResourceEncoding.LZW if compressed else ResourceEncoding.LIBHDR
    resources = {
        "palette": ResourceSpec(palette),
        "look": ResourceSpec("look.lzd" if compressed else "look.lzc", encoding),
        "tileflag": ResourceSpec("tileflag"),
        "tileindx": ResourceSpec("tileindx.vga"),
        "animdata": ResourceSpec("animdata"),
        "masktypes": ResourceSpec("masktype.vga", encoding),
        "maptiles": ResourceSpec("maptiles.vga", encoding),
        "objtiles": ResourceSpec("objtiles.vga"),
        "animmask": ResourceSpec(
            "animmask.vga",
            ResourceEncoding.LZW if compressed else ResourceEncoding.EMPTY,
        ),
        "basetile": ResourceSpec("basetile"),
        "chunks": ResourceSpec("chunks"),
        "map": ResourceSpec("map"),
        "objlist": ResourceSpec("savegame/objlist"),
        "books": ResourceSpec(
            "book.dat",
            ResourceEncoding.RAW if compressed else ResourceEncoding.EMPTY,
        ),
        "font": ResourceSpec("u6.ch", required=False),
    }
    resources.update(
        (filename, ResourceSpec(filename)) for filename in OBJECT_BLOCK_FILES
    )
    return GameManifest(game, palette, resources)


SUPPORTED_GAMES: Final[Mapping[GameType, GameManifest]] = MappingProxyType(
    {
        GameType.FP: _manifest(GameType.FP, "u6pal", compressed=True),
        GameType.MD: _manifest(GameType.MD, "mdpal", compressed=False),
        GameType.SE: _manifest(GameType.SE, "sepal", compressed=False),
    }
)


def get_manifest(game: GameType | str) -> GameManifest:
    """Parse a game identifier and return its immutable installation manifest."""
    return SUPPORTED_GAMES[GameType(game)]


def palette_filename(game: GameType | str) -> str:
    """Return the palette filename that identifies a game installation."""
    return get_manifest(game).palette_name


def required_game_files(game: GameType | str) -> tuple[str, ...]:
    """Return the complete installation checklist used by profile inspection."""
    return get_manifest(game).required_files


def resolve_dos_path(path: Path | str) -> Path:
    """Resolve existing path components case-insensitively, retaining disk case."""
    requested = Path(path)
    current = Path(requested.anchor) if requested.is_absolute() else Path.cwd()
    components = requested.parts[1:] if requested.is_absolute() else requested.parts
    for component in components:
        candidate = current / component
        if current.is_dir():
            current = next(
                (
                    entry
                    for entry in current.iterdir()
                    if entry.name.casefold() == component.casefold()
                ),
                candidate,
            )
        else:
            current = candidate
    return current


def decode_resource(directory: Path, game: GameType | str, key: str) -> bytes:
    """Read one manifest resource without changing the process working directory."""
    spec = get_manifest(game).resources[key]
    if spec.encoding & ResourceEncoding.EMPTY:
        return b""
    path = resolve_dos_path(directory / spec.filename)
    data = path.read_bytes()
    if spec.encoding & ResourceEncoding.LZW:
        data = decompress_buffer(data)
    if spec.encoding & ResourceEncoding.LIBHDR:
        if len(data) < 6:
            raise FormatError(spec.filename, "truncated library header")
        declared = int.from_bytes(data[:4], "little")
        start = int.from_bytes(data[4:6], "little")
        if len(data) != declared:
            raise FormatError(
                spec.filename,
                f"file size {len(data)} does not match header size {declared}",
            )
        if not 6 <= start <= len(data):
            raise FormatError(spec.filename, f"invalid library data offset {start}")
        data = data[start:]
    return data
