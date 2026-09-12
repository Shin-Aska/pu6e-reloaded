"""Session-bound map renderer with explicit Qt OpenGL context ownership."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import TYPE_CHECKING

from game.models.coordinates import block_to_world, world_to_block
from game.models.game import GameType
from ui.rendering import batch, overlays
from ui.rendering.gl_api import GL
from ui.rendering.textures import TextureSet

if TYPE_CHECKING:
    from game.services.session import WorldSession
    from ui.rendering.camera import CameraState
    from ui.rendering.options import RenderOptions


@dataclass(frozen=True, slots=True)
class BlockPlacement:
    """A wrapped object-block ID and its unscaled viewport-pixel origin."""

    block: int
    x: int
    y: int


def visible_blocks(camera: CameraState, width: int, height: int) -> tuple[BlockPlacement, ...]:
    """Include visible blocks and neighboring anchors of multi-tile objects."""
    world_x, world_y, world_z = camera.coords
    block_size = 128 if world_z == 0 else 256
    start_x = -(world_x % block_size) * 16
    start_y = -(world_y % block_size) * 16
    return tuple(
        BlockPlacement(
            world_to_block(world_x + column * block_size, world_y + row * block_size, world_z), x, y
        )
        for row, y in enumerate(range(start_y, height + 16, block_size * 16))
        for column, x in enumerate(range(start_x, width + 16, block_size * 16))
    )


class MapRenderer:
    """Owns one session's GL resources; Qt must make its context current for all GL methods."""

    def __init__(self, session: WorldSession, camera: CameraState, options: RenderOptions) -> None:
        self.session: WorldSession = session
        self.camera: CameraState = camera
        self.options: RenderOptions = options
        self.resources: TextureSet | None = None
        self.game_timer: int = 0

    @property
    def initialized(self) -> bool:
        """Report whether the renderer currently owns uploaded GL resources."""
        return self.resources is not None

    def initialize(self, width: int, height: int) -> None:
        """Create resources and projection using the current Qt context."""
        self.dispose()
        resources = TextureSet(self.session.state.assets)
        completed = False
        try:
            resources.create()
            if self.session.state.game_type != GameType.MD:
                resources.update_animation(0)
            GL.glEnable(GL.GL_TEXTURE_2D)
            GL.glClearColor(0.0, 0.0, 0.0, 0.0)
            GL.glClearDepth(1.0)
            GL.glDepthFunc(GL.GL_LEQUAL)
            GL.glShadeModel(GL.GL_FLAT)
            GL.glAlphaFunc(GL.GL_GREATER, 0.01)
            self.resources = resources
            self.resize(width, height)
            completed = True
        finally:
            if not completed:
                resources.dispose()
                self.resources = None

    def resize(self, width: int, height: int) -> None:
        """Update camera bounds and the current-context projection."""
        self.camera.resize(width, height)
        if not self.initialized:
            return
        GL.glViewport(0, 0, width, height)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(
            0, max(1, width) / self.camera.scale, max(1, height) / self.camera.scale, 0, -100, 100
        )
        GL.glMatrixMode(GL.GL_MODELVIEW)

    def set_session(self, session: WorldSession) -> None:
        """Replace session resources, releasing old textures in the current context."""
        if session is self.session:
            return
        initialized = self.initialized
        self.dispose()
        self.session = session
        self.game_timer = 0
        if initialized:
            self.initialize(self.camera.width, self.camera.height)

    def tick(self) -> None:
        """Advance this renderer animation clock without issuing GL calls."""
        self.game_timer += 1

    def paint(self) -> None:
        """Paint one frame using the current Qt context."""
        resources = self.resources
        if resources is None:
            return
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        if self.options.rotate_palette:
            resources.update_palette(self.game_timer)
        if self.options.animate_tiles and self.session.state.game_type != GameType.MD:
            resources.update_animation(self.game_timer)
        if self.options.hybrid_tiles:
            resources.update_hybrids()
        self._draw_map(resources)
        if self.options.display_coords:
            overlays.draw_coords(self.camera, resources)

    def _draw_map(self, resources: TextureSet) -> None:
        width = ceil(self.camera.width / self.camera.scale)
        height = ceil(self.camera.height / self.camera.scale)
        stride = (width + 15) & ~15
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_BLEND)
        GL.glDisable(GL.GL_ALPHA_TEST)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_REPLACE)
        GL.glBindTexture(GL.GL_TEXTURE_2D, resources.atlas)
        terrain = self.session.state.terrain
        batch.draw_maptiles(
            0, 0, *self.camera.coords, stride, height, terrain.superchunks, terrain.chunks
        )
        if self.options.display_grid:
            overlays.draw_grid(width, height, self.camera, self.session, resources)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glEnable(GL.GL_ALPHA_TEST)
        GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glColor4f(1.0, 1.0, 1.0, 1.0)
        if self.options.display_objects or self.options.fade_objects >= 0.0:
            if self.options.fade_objects >= 0.0:
                GL.glColor4f(1.0, 1.0, 1.0, self.options.fade_objects)
                self.options.fade_objects -= 0.33
            blocks = visible_blocks(self.camera, stride, height)
            for draw_height in (0, 1):
                ordered = reversed(blocks) if draw_height == 0 else iter(blocks)
                for placement in ordered:
                    world_x, world_y, _ = block_to_world(placement.block)
                    batch.draw_objblk(
                        placement.block,
                        world_x,
                        world_y,
                        placement.x,
                        placement.y,
                        draw_height,
                        stride,
                        height,
                        self.session.state.object_blocks,
                        resources.textures,
                        self.session.state.assets.catalog,
                    )

    def dispose(self) -> None:
        """Release owned textures in the current context; repeated calls are harmless."""
        resources = self.resources
        if resources is not None:
            resources.dispose()
            self.resources = None
