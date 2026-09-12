from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

from ui.rendering.camera import CameraState, InvalidZoomError
from ui.rendering.options import RenderOptions

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    import numpy as np
    from numpy.typing import NDArray
from game.models.assets import (
    AnimationData,
    HybridMask,
    ObjectCatalog,
    Palette,
    TileSet,
    WorldAssets,
)
from game.models.game import GameType
from game.models.world import WorldMap, WorldState
from game.services.session import WorldSession
from ui.rendering import gl_api
from ui.rendering.gl_api import GL, OpenGLBindingError
from ui.rendering.renderer import MapRenderer, visible_blocks


def test_camera_preserves_center_when_resized_and_zoomed() -> None:
    # Given a camera centered across a world boundary.
    camera = CameraState(position=(1023, 0, 0))
    # When framebuffer dimensions and zoom change.
    camera.resize(800, 600)
    camera.set_zoom(2.0)
    # Then the center remains selected and screen input resolves there.
    assert camera.position == (1023, 0, 0)
    assert camera.center_offset == (12, 9)
    assert camera.screen_to_world(400, 300) == (1023, 0, 0)
    assert camera.coords == (1011, 1015, 0)


def test_camera_and_options_are_independent_between_instances() -> None:
    # Given independently owned states.
    first, second = CameraState(), CameraState()
    options, other_options = RenderOptions(), RenderOptions()
    # When one controller changes its camera and options.
    first.set_position(1, 2, 3)
    first.resize(1600, 1200)
    first.set_zoom(4.0)
    options.display_grid = True
    # Then the second state keeps its defaults.
    assert second.position == (0, 0, 0)
    assert second.scale == 1.0
    assert second.center_offset == (0, 0)
    assert not other_options.display_grid


@pytest.mark.parametrize(("level", "width"), [(0, 1024), (1, 256), (5, 256)])
def test_camera_wraps_screen_coordinates_at_each_world_size(level: int, width: int) -> None:
    # Given the upper-left corner at the final tile.
    camera = CameraState(position=(width - 1, width - 1, level))
    # When input extends beyond the edge or before the origin.
    right = camera.screen_to_world(16, 16)
    left = camera.screen_to_world(-1, -1)
    # Then tiles wrap, with negative pixels rounding down.
    assert right == (0, 0, level)
    assert left == (width - 2, width - 2, level)


def test_camera_wraps_level_before_selecting_world_size() -> None:
    # Given a requested level that wraps onto the surface.
    camera = CameraState()
    # When its center changes.
    camera.set_position(900, -1, 6)
    # Then wrapping uses the destination level's dimensions.
    assert camera.position == (900, 1023, 0)


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan"), float("inf")])
def test_camera_rejects_invalid_zoom(scale: float) -> None:
    # Given a usable camera.
    camera = CameraState()
    # When an invalid scale is requested, then the camera keeps its old scale.
    with pytest.raises(InvalidZoomError):
        camera.set_zoom(scale)
    assert camera.scale == 1.0


@dataclass(slots=True)  # noqa: RUF100  # noqa: MUTABLE_OK
class GLTrace:
    """Mutable recorder for GPU allocation and upload calls without a native test context."""

    allocated: list[int] = field(default_factory=list)
    deleted: list[int] = field(default_factory=list)
    uploads: list[tuple[int, int, bytes]] = field(default_factory=list)

    def create(self, _count: int) -> int:
        handle = len(self.allocated) + 1
        self.allocated.append(handle)
        return handle

    def delete(self, handles: Sequence[int]) -> None:
        self.deleted.extend(handles)

    def upload(
        self,
        _target: int,
        _level: int,
        x: int,
        y: int,
        _width: int,
        _height: int,
        _format: int,
        _kind: int,
        pixels: bytes,
    ) -> None:
        self.uploads.append((x, y, pixels))


def _record_gl(monkeypatch: pytest.MonkeyPatch) -> GLTrace:
    trace = GLTrace()

    def noop(*_args: float | bytes | Sequence[int] | NDArray[np.float32]) -> None:
        return None

    for name in (
        "glBindTexture",
        "glPixelStorei",
        "glTexImage2D",
        "glTexParameterf",
        "glEnable",
        "glClearColor",
        "glClearDepth",
        "glDepthFunc",
        "glShadeModel",
        "glAlphaFunc",
        "glViewport",
        "glMatrixMode",
        "glLoadIdentity",
        "glOrtho",
        "glClear",
        "glDisable",
        "glTexEnvf",
        "glBlendFunc",
        "glColor4f",
        "glEnableClientState",
        "glDisableClientState",
        "glVertexPointer",
        "glTexCoordPointer",
        "glDrawArrays",
    ):
        monkeypatch.setattr(GL, name, noop)
    monkeypatch.setattr(GL, "glGenTextures", trace.create)
    monkeypatch.setattr(GL, "glDeleteTextures", trace.delete)
    monkeypatch.setattr(GL, "glTexSubImage2D", trace.upload)
    return trace


def _session(game: GameType = GameType.FP) -> WorldSession:
    palette = Palette(tuple((index, index, index) for index in range(256)))
    catalog = ObjectCatalog(tuple(range(1024)), (0,) * 0x1600, {})
    pixels = tuple(bytes((index % 224,)) * 256 for index in range(512))
    animations = AnimationData(1, (0,), (256,), (1,), (0,))
    assets = WorldAssets(
        palette, TileSet(pixels, catalog.tile_flags, (), animations, ()), catalog, None, ()
    )
    terrain = WorldMap(
        [[0] * (256 if block < 64 else 1024) for block in range(69)], [bytearray(64)]
    )
    return WorldSession(WorldState(game, Path(), terrain, [[] for _ in range(69)], [], assets))


def test_session_replacement_releases_only_own_textures(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given two renderers initialized into independent resource sets.
    trace = _record_gl(monkeypatch)
    first = MapRenderer(_session(), CameraState(), RenderOptions())
    second = MapRenderer(_session(), CameraState(), RenderOptions())
    first.initialize(32, 32)
    second.initialize(32, 32)
    assert first.resources is not None
    assert second.resources is not None
    old_first = tuple(first.resources.handles)
    second_handles = tuple(second.resources.handles)
    # When the first renderer switches sessions.
    first.set_session(_session())
    # Then old handles are deleted once without touching the second renderer.
    assert trace.deleted == list(old_first)
    assert second.resources.handles == list(second_handles)
    assert first.resources is not None
    assert set(first.resources.handles).isdisjoint(second_handles)


def test_renderer_disposal_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given one fully initialized renderer.
    trace = _record_gl(monkeypatch)
    renderer = MapRenderer(_session(), CameraState(), RenderOptions())
    renderer.initialize(32, 32)
    # When Qt issues repeated disposal callbacks.
    renderer.dispose()
    renderer.dispose()
    # Then every allocation is released exactly once.
    assert trace.deleted == trace.allocated
    assert not renderer.initialized


def test_md_does_not_upload_animated_canal_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given Mars with an animation table and no palette cycling.
    trace = _record_gl(monkeypatch)
    renderer = MapRenderer(
        _session(GameType.MD), CameraState(), RenderOptions(rotate_palette=False)
    )
    renderer.initialize(32, 32)
    initial_uploads = len(trace.uploads)
    # When the timer advances and the scene paints.
    renderer.tick()
    renderer.paint()
    # Then the atlas remains on its original canal artwork.
    assert initial_uploads == 256
    assert len(trace.uploads) == initial_uploads


def test_animated_terrain_uses_current_frame_without_mutating_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given animated terrain with two distinct frame colors.
    trace = _record_gl(monkeypatch)
    session = _session()
    renderer = MapRenderer(session, CameraState(), RenderOptions(rotate_palette=False))
    renderer.initialize(32, 32)
    original = session.state.assets.tiles.pixels
    # When one tick advances the frame and paints.
    renderer.tick()
    renderer.paint()
    # Then the first atlas slot receives frame 257, preserving the indexed source assets.
    assert trace.uploads[-1] == (0, 0, bytes((33, 33, 33, 255)) * 256)
    assert session.state.assets.tiles.pixels is original
    assert original[0] == bytes(256)


def test_visible_blocks_include_wrapped_offscreen_object_anchors() -> None:
    # Given a viewport ending exactly at the surface boundary.
    camera = CameraState(position=(1023, 1023, 0))
    # When collecting blocks for the visible tile and neighboring large-object anchors.
    blocks = visible_blocks(camera, 16, 16)
    # Then all four blocks participate across both wrapped edges.
    assert [(entry.block, entry.x, entry.y) for entry in blocks] == [
        (63, -2032, -2032),
        (56, 16, -2032),
        (7, -2032, 16),
        (0, 16, 16),
    ]


class TextureUploadError(RuntimeError):
    pass


def test_failed_texture_initialization_releases_partial_allocations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a driver which fails after allocating its first texture.
    trace = _record_gl(monkeypatch)
    renderer = MapRenderer(_session(), CameraState(), RenderOptions())

    def fail_upload(*_args: int | bytes) -> None:
        raise TextureUploadError

    monkeypatch.setattr(GL, "glTexImage2D", fail_upload)
    # When texture initialization cannot finish.
    with pytest.raises(TextureUploadError):
        renderer.initialize(32, 32)
    # Then every partial allocation is released and rendering remains uninitialized.
    assert trace.deleted == trace.allocated == [1]
    assert not renderer.initialized


def test_hybrid_masks_copy_current_animation_pixels_without_changing_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a hybrid tile borrowing only its first RGBA pixel from animated terrain.
    trace = _record_gl(monkeypatch)
    session = _session()
    original = session.state.assets.tiles
    hybrid = HybridMask(1, 0, bytes((255,)) * 4 + bytes(1020))
    session.state.assets = replace(session.state.assets, tiles=replace(original, hybrids=(hybrid,)))
    renderer = MapRenderer(
        session, CameraState(), RenderOptions(rotate_palette=False, hybrid_tiles=True)
    )
    renderer.initialize(32, 32)
    # When animation advances and the hybrid is composed.
    renderer.tick()
    renderer.paint()
    # Then the mask selects frame 257 while leaving all other destination pixels intact.
    assert trace.uploads[-1] == (16, 0, bytes((33, 33, 33, 255)) + bytes((1, 1, 1, 255)) * 255)
    assert session.state.assets.tiles.pixels is original.pixels


@contextmanager
def _propagation_scope() -> Generator[None]:
    yield


def test_invalid_camera_zoom_propagates_through_context_managers() -> None:
    # Given a valid camera accessed inside generator-based context management.
    camera = CameraState()
    # When zoom validation fails, then its original error reaches the caller.
    with pytest.raises(InvalidZoomError) as caught, _propagation_scope():
        camera.set_zoom(0.0)
    assert caught.value.scale == 0.0
    assert camera.scale == 1.0


def test_incomplete_gl_bindings_propagate_through_context_managers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given an imported OpenGL module missing its required compatibility functions.
    def load_incomplete_bindings(name: str) -> ModuleType:
        return ModuleType(name)

    monkeypatch.setattr(gl_api, "import_module", load_incomplete_bindings)
    # When the real boundary checks it, then its typed error keeps a writable traceback.
    with pytest.raises(OpenGLBindingError) as caught, _propagation_scope():
        _ = gl_api.load_gl()
    assert caught.value.module == "OpenGL.GL"
