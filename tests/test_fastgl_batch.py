from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
import pytest

import fastgl
from U6 import Map


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
        size: int,
        gl_type: int,
        stride: int,
        vertices: NDArray[np.float32],
    ) -> None:
        captured["vertices"] = vertices.copy()

    def capture_texture_coordinates(
        size: int,
        gl_type: int,
        stride: int,
        coordinates: NDArray[np.float32],
    ) -> None:
        captured["coordinates"] = coordinates.copy()

    monkeypatch.setattr(fastgl.GL, "glEnableClientState", lambda *_args: None)
    monkeypatch.setattr(fastgl.GL, "glDisableClientState", lambda *_args: None)
    monkeypatch.setattr(fastgl.GL, "glVertexPointer", capture_vertices)
    monkeypatch.setattr(fastgl.GL, "glTexCoordPointer", capture_texture_coordinates)
    monkeypatch.setattr(fastgl.GL, "glDrawArrays", lambda *args: draw_calls.append(args))
    monkeypatch.setattr(
        fastgl.GL,
        "glTexCoord2f",
        lambda *_args: pytest.fail("terrain still submits individual texture coordinates"),
    )

    fastgl.draw_maptiles(4, 6, world_x, world_y, world_z, 36, 38, maps, chunks)

    assert draw_calls == [(fastgl.GL.GL_QUADS, 0, 16)]
    assert captured["vertices"].shape == (16, 3)
    np.testing.assert_array_equal(
        captured["vertices"][:4],
        np.array([[4, 6, 0], [20, 6, 0], [20, 22, 0], [4, 22, 0]], dtype=np.float32),
    )

    expected_tiles = []
    for offset_y in range(2):
        for offset_x in range(2):
            scx, scy, cx, cy, tx, ty = Map.world_to_chunk(
                world_x + offset_x,
                world_y + offset_y,
                world_z,
            )
            chunk_width = 16 if world_z == 0 else 32
            chunk = maps[scx + scy * 8][cx + cy * chunk_width]
            expected_tiles.append(chunks[chunk][tx + ty * 8])

    for index, tile in enumerate(expected_tiles):
        np.testing.assert_array_equal(
            captured["coordinates"][index * 4],
            np.array([tile % 16 / 16, tile // 16 / 16], dtype=np.float32),
        )
