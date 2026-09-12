from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from numpy.typing import NDArray

from pu6e_core.models.assets import ObjectCatalog, Palette
from pu6e_core.models.coordinates import world_to_chunk
from pu6e_core.models.objects import ObjectPoint, WorldObject
from pu6e_qt.rendering import batch, pixels
from pu6e_qt.rendering.gl_api import GL


@pytest.mark.parametrize(("world_x", "world_y", "world_z"), [(1023, 1023, 0), (255, 255, 1)])
def test_map_tiles_use_one_batched_draw_with_wrapped_world_coordinates(
    monkeypatch: pytest.MonkeyPatch,
    world_x: int,
    world_y: int,
    world_z: int,
) -> None:
    maps = [[index] * 1024 for index in range(69)]
    chunks = [[(index + offset) % 256 for offset in range(64)] for index in range(69)]
    captured: dict[str, NDArray[np.float32]] = {}
    draw_calls: list[tuple[int, int, int]] = []

    def capture_vertices(
        _size: int,
        _gl_type: int,
        _stride: int,
        vertices: NDArray[np.float32],
    ) -> None:
        captured["vertices"] = vertices.copy()

    def capture_texture_coordinates(
        _size: int,
        _gl_type: int,
        _stride: int,
        coordinates: NDArray[np.float32],
    ) -> None:
        captured["coordinates"] = coordinates.copy()

    def noop(_capability: int) -> None:
        return None

    def record_draw(mode: int, first: int, count: int) -> None:
        draw_calls.append((mode, first, count))

    def reject_individual_coordinates(_s: float, _t: float) -> None:
        pytest.fail("terrain still submits individual texture coordinates")

    monkeypatch.setattr(GL, "glEnableClientState", noop)
    monkeypatch.setattr(GL, "glDisableClientState", noop)
    monkeypatch.setattr(GL, "glVertexPointer", capture_vertices)
    monkeypatch.setattr(GL, "glTexCoordPointer", capture_texture_coordinates)
    monkeypatch.setattr(GL, "glDrawArrays", record_draw)
    monkeypatch.setattr(
        GL,
        "glTexCoord2f",
        reject_individual_coordinates,
    )

    batch.draw_maptiles(4, 6, world_x, world_y, world_z, 36, 38, maps, chunks)

    assert draw_calls == [(GL.GL_QUADS, 0, 16)]
    assert captured["vertices"].shape == (16, 3)
    np.testing.assert_array_equal(
        captured["vertices"][:4],
        np.array([[4, 6, 0], [20, 6, 0], [20, 22, 0], [4, 22, 0]], dtype=np.float32),
    )

    expected_tiles: list[int] = []
    for offset_y in range(2):
        for offset_x in range(2):
            scx, scy, cx, cy, tx, ty = world_to_chunk(
                world_x + offset_x,
                world_y + offset_y,
                world_z,
            )
            chunk_width = 16 if world_z == 0 else 32
            chunk = maps[scx + scy * 8][cx + cy * chunk_width]
            expected_tiles.append(chunks[chunk][tx + ty * 8])

    for index, tile in enumerate(expected_tiles):
        np.testing.assert_array_equal(
            captured["coordinates"][index * 4 : index * 4 + 1],
            np.array([[tile % 16 / 16, tile // 16 / 16]], dtype=np.float32),
        )


def test_object_batch_draws_all_large_parts_in_anchor_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    # Given a four-part object whose anchor is inside the viewport.
    calls: list[tuple[int, int, int, int]] = []
    flags = [0] * 0x1600
    flags[0x800 + 12] = 3 << 6
    catalog = ObjectCatalog(tuple(range(1024)), tuple(flags), {})
    point = ObjectPoint(4, 5, 0)
    point.append(WorldObject(catalog, packed_type=12))
    blocks = [[(5, [(4, point)])]]

    def record(texture: int, x: int, y: int, z: int) -> None:
        calls.append((texture, x, y, z))

    monkeypatch.setattr(batch, "draw_poly_tex", record)
    # When its lower-height pass is drawn.
    batch.draw_objblk(0, 4, 5, 16, 16, 0, 128, 128, blocks, tuple(range(32)), catalog)
    # Then each tile uses its own texture and anchor-relative placement.
    assert calls == [(12, 16, 16, 0), (11, 0, 16, 0), (10, 16, 0, 0), (9, 0, 0, 0)]


def test_object_height_pass_reverses_points_without_mutating_world(
    monkeypatch: pytest.MonkeyPatch,
) -> None:

    # Given descending points carrying overlapping tall objects.
    flags = [0] * 0x1600
    flags[0x800 + 12] = flags[0x800 + 13] = 1 << 4
    catalog = ObjectCatalog(tuple(range(1024)), tuple(flags), {})
    east, west = ObjectPoint(1, 0, 0), ObjectPoint(0, 0, 0)
    east.append(WorldObject(catalog, packed_type=13))
    west.append(WorldObject(catalog, packed_type=12))
    blocks = [[(0, [(1, east), (0, west)])]]
    calls: list[int] = []

    def record(texture: int, _x: int, _y: int, _z: int) -> None:
        calls.append(texture)

    monkeypatch.setattr(batch, "draw_poly_tex", record)
    # When the upper-height pass traverses the block.
    batch.draw_objblk(0, 0, 0, 0, 0, 1, 128, 128, blocks, tuple(range(32)), catalog)
    # Then west precedes east and the world's stored order is intact.
    assert calls == [12, 13]
    assert [x for x, _ in blocks[0][0][1]] == [1, 0]


def test_indexed_pixels_keep_transparency_and_palette_animation() -> None:

    # Given opaque, cycling, and transparent palette entries.
    palette = Palette(tuple((index, index, index) for index in range(256)))
    # When object pixels are expanded to RGBA.
    rgba, animated = pixels.indexed_to_rgba(bytes((1, 0xE0, 0xFF)), palette)
    # Then only the transparent index loses alpha and cycling is reported.
    assert rgba == bytes((1, 1, 1, 255, 224, 224, 224, 255, 255, 255, 255, 0))
    assert animated


def test_palette_cycles_do_not_mutate_shared_palette() -> None:

    # Given a shared palette and all eight animation steps.
    palette = Palette(tuple((index, 0, 0) for index in range(256)))
    # When the renderer builds its private cycle values.
    rotations = pixels.palette_cycles(palette)
    # Then long cycles advance each tick and short cycles every other tick.
    assert [entry.colors[0xE0][0] for entry in rotations] == [
        224,
        231,
        230,
        229,
        228,
        227,
        226,
        225,
    ]
    assert [entry.colors[0xF0][0] for entry in rotations] == [
        240,
        240,
        243,
        243,
        242,
        242,
        241,
        241,
    ]
    assert palette.colors[0xE0] == (224, 0, 0)


def test_font_mask_expands_to_native_rgba_pixels() -> None:

    # Given one on pixel and 63 off pixels.
    mask = bytes((0x48,)) + bytes(63)
    # When converted for a glyph texture.
    rgba = pixels.fontchar_to_rgba(mask)
    # Then each pixel occupies four bytes with white or transparent output.
    assert rgba == bytes((255, 255, 255, 255)) + bytes(63 * 4)
