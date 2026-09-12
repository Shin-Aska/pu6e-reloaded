"""Game-font coordinate and chunk-grid overlays."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pu6e_qt.rendering.batch import draw_poly_tex
from pu6e_qt.rendering.gl_api import GL

if TYPE_CHECKING:
    from pu6e_core.models.assets import Palette
    from pu6e_core.services.session import WorldSession
    from pu6e_qt.rendering.camera import CameraState
    from pu6e_qt.rendering.textures import TextureSet


def draw_font_str(text: str, x: int, y: int, z: int, glyphs: tuple[int, ...]) -> None:
    """Draw game glyphs at their original sixteen-pixel display size."""
    for character in text:
        draw_poly_tex(glyphs[ord(character)], x, y, z)
        x += 16


def draw_text_bg(x: int, y: int, width: int, height: int, palette: Palette) -> None:
    """Draw the translucent game-palette text background."""
    GL.glDisable(GL.GL_TEXTURE_2D)
    red, green, blue = palette.colors[0x31]
    GL.glColor4f(red / 255, green / 255, blue / 255, 0.8)
    GL.glBegin(GL.GL_QUADS)
    for vx, vy in ((x, y), (x + width, y), (x + width, y + height), (x, y + height)):
        GL.glVertex3f(vx, vy, 0)
    GL.glEnd()


def draw_coords(camera: CameraState, resources: TextureSet) -> None:
    """Draw centered world coordinates in fixed framebuffer-pixel scale."""
    glyphs = resources.fontchars
    if glyphs is None:
        return
    GL.glEnable(GL.GL_BLEND)
    GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    GL.glMatrixMode(GL.GL_PROJECTION)
    GL.glPushMatrix()
    try:
        GL.glLoadIdentity()
        GL.glOrtho(0, camera.width, camera.height, 0, -100, 100)
        x, y = camera.width - 200, 20
        draw_text_bg(x - 5, y - 5, 154, 26, resources.assets.palette)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
        GL.glColor4f(0, 0, 0, 0.7)
        world_x, world_y, world_z = camera.position
        text = f"{world_x:03x} {world_y:03x} {world_z}"
        draw_font_str(text, x + 1, y + 1, 0, glyphs)
        red, green, blue = resources.assets.palette.colors[0x48]
        GL.glColor4f(red / 255, green / 255, blue / 255, 1.0)
        draw_font_str(text, x, y, 0, glyphs)
    finally:
        GL.glPopMatrix()
        GL.glMatrixMode(GL.GL_MODELVIEW)


def draw_grid(
    width: int,
    height: int,
    camera: CameraState,
    session: WorldSession,
    resources: TextureSet,
) -> None:
    """Draw chunk boundaries and chunk numbers aligned with the world origin."""
    world_x, world_y, world_z = camera.coords
    start_x, start_y = -(world_x % 8) * 16, -(world_y % 8) * 16
    GL.glDisable(GL.GL_TEXTURE_2D)
    GL.glEnable(GL.GL_BLEND)
    GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)
    GL.glColor4f(1.0, 0.8, 0.7, 0.6)
    GL.glBegin(GL.GL_QUADS)
    for x in range(start_x, width + 128, 128):
        for vx, vy in ((x - 1, 0), (x + 1, 0), (x + 1, height), (x - 1, height)):
            GL.glVertex3f(vx, vy, 1)
    for y in range(start_y, height + 128, 128):
        for vx, vy in ((0, y - 1), (width, y - 1), (width, y + 1), (0, y + 1)):
            GL.glVertex3f(vx, vy, 1)
    GL.glEnd()
    glyphs = resources.fontchars
    if glyphs is None:
        return
    GL.glEnable(GL.GL_TEXTURE_2D)
    GL.glTexEnvf(GL.GL_TEXTURE_ENV, GL.GL_TEXTURE_ENV_MODE, GL.GL_MODULATE)
    for row, y in enumerate(range(start_y, height, 128)):
        for column, x in enumerate(range(start_x, width, 128)):
            chunk, _, _ = session.editor.chunk_at(world_x + column * 8, world_y + row * 8, world_z)
            GL.glColor4f(0, 0, 0, 0.7)
            draw_font_str(str(chunk), x + 21, y + 21, 0, glyphs)
            GL.glColor4f(1.0, 0.8, 0.8, 0.8)
            draw_font_str(str(chunk), x + 20, y + 20, 0, glyphs)
