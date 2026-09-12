"""Per-controller display and animation options."""

from dataclasses import dataclass


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class RenderOptions:
    """Mutable display choices shared by one controller and its renderer."""

    display_grid: bool = False
    display_objects: bool = True
    display_coords: bool = True
    animate_tiles: bool = True
    rotate_palette: bool = True
    hybrid_tiles: bool = False
    fade_objects: float = 0.0
