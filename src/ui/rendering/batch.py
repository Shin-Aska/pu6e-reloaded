# ruff: noqa: PLR0913, PLR0917
# Explicit coordinates and asset inputs keep draw submission stateless.
"""Stateless terrain and object submission preserving the game painter order."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from game.models.coordinates import world_to_chunk
from ui.rendering.gl_api import GL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from numpy.typing import NDArray

    from game.models.assets import ObjectCatalog
    from game.models.objects import ObjectBlock, WorldObject


def draw_poly_tex(texture: int, x: int, y: int, z: int) -> None:
    """Draw one object or glyph texture at the requested painter height."""
    GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
    GL.glBegin(GL.GL_QUADS)
    for tx, ty, vx, vy in (
        (0, 0, x, y),
        (1, 0, x + 16, y),
        (1, 1, x + 16, y + 16),
        (0, 1, x, y + 16),
    ):
        GL.glTexCoord2f(tx, ty)
        GL.glVertex3f(vx, vy, z)
    GL.glEnd()


def draw_maptiles(
    x: int,
    y: int,
    wx: int,
    wy: int,
    wz: int,
    stride: int,
    height: int,
    maps: Sequence[Sequence[int]],
    chunks: Sequence[Sequence[int]],
) -> None:
    """Submit all visible terrain in one draw with atlas coordinates and world wrapping."""
    columns = max(0, (stride - x + 15) // 16)
    rows = max(0, (height - y + 15) // 16)
    if not columns or not rows:
        return
    chunk_width = 16 if wz == 0 else 32
    tile_ids: NDArray[np.float32] = np.asarray(
        [
            chunks[maps[scx + scy * 8][cx + cy * chunk_width]][tx + ty * 8]
            for world_y in range(wy, wy + rows)
            for world_x in range(wx, wx + columns)
            for scx, scy, cx, cy, tx, ty in (world_to_chunk(world_x, world_y, wz),)
        ],
        dtype=np.float32,
    ).reshape(rows, columns)
    vertices: NDArray[np.float32] = np.empty((rows, columns, 4, 3), dtype=np.float32)
    vertices[..., 0] = (
        np.arange(columns, dtype=np.float32)[None, :, None] * 16 + x + (0.0, 16.0, 16.0, 0.0)
    )
    vertices[..., 1] = (
        np.arange(rows, dtype=np.float32)[:, None, None] * 16 + y + (0.0, 0.0, 16.0, 16.0)
    )
    vertices[..., 2] = 0.0
    texture_coordinates: NDArray[np.float32] = np.empty((rows, columns, 4, 2), dtype=np.float32)
    texture_coordinates[..., 0] = (tile_ids % 16)[..., None] / 16 + (
        0.0,
        0.0625,
        0.0625,
        0.0,
    )
    texture_coordinates[..., 1] = (tile_ids // 16)[..., None] / 16 + (
        0.0,
        0.0,
        0.0625,
        0.0625,
    )
    GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
    GL.glEnableClientState(GL.GL_TEXTURE_COORD_ARRAY)
    try:
        GL.glVertexPointer(3, GL.GL_FLOAT, 0, vertices.reshape(-1, 3))
        GL.glTexCoordPointer(2, GL.GL_FLOAT, 0, texture_coordinates.reshape(-1, 2))
        GL.glDrawArrays(GL.GL_QUADS, 0, rows * columns * 4)
    finally:
        GL.glDisableClientState(GL.GL_TEXTURE_COORD_ARRAY)
        GL.glDisableClientState(GL.GL_VERTEX_ARRAY)


def _draw_object_parts(
    item: WorldObject,
    x: int,
    y: int,
    draw_height: int,
    stride: int,
    height: int,
    textures: Sequence[int],
    catalog: ObjectCatalog,
) -> None:
    tile = item.tile

    def draw(part: int, part_x: int, part_y: int) -> None:
        if not (0 <= part_x < stride and 0 <= part_y < height):
            return
        z = catalog.height(part)
        if draw_height == z:
            draw_poly_tex(textures[part], part_x, part_y, z)

    if x < stride + 16 and y < height + 16:
        z = catalog.height(tile)
        if draw_height == z:
            draw_poly_tex(textures[tile], x, y, z)
    size = catalog.size(tile)
    if size & 2:
        tile -= 1
        draw(tile, x - 16, y)
    if size & 1:
        tile -= 1
        draw(tile, x, y - 16)
        if size & 2:
            tile -= 1
            draw(tile, x - 16, y - 16)


def draw_objblk(
    block: int,
    wx: int,
    wy: int,
    sx: int,
    sy: int,
    draw_height: int,
    stride: int,
    height: int,
    object_blocks: Sequence[ObjectBlock],
    textures: Sequence[int],
    catalog: ObjectCatalog,
) -> None:
    """Preserve descending ground order, ascending height order, and point stack order."""
    rows = object_blocks[block]
    ordered_rows = iter(rows) if draw_height == 0 else reversed(rows)
    for oy, row in ordered_rows:
        if oy < wy:
            if draw_height == 0:
                break
            continue
        y = sy + 16 * (oy - wy)
        if y >= height + 16:
            if draw_height == 1:
                break
            continue
        points = iter(row) if draw_height == 0 else reversed(row)
        for ox, point in points:
            if ox < wx:
                continue
            x = sx + 16 * (ox - wx)
            if x >= stride + 16:
                continue
            for item in point:
                _draw_object_parts(item, x, y, draw_height, stride, height, textures, catalog)
