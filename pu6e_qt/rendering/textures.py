"""Renderer-owned texture allocation, animation caches, and cleanup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import numpy as np

from pu6e_qt.rendering.gl_api import GL
from pu6e_qt.rendering.pixels import fontchar_to_rgba, indexed_to_rgba, palette_cycles

if TYPE_CHECKING:
    from pu6e_core.models.assets import WorldAssets


BACKGROUND_TILE_COUNT: Final = 256
CACHED_TILE_COUNT: Final = 512


class TextureSet:
    """Mutable GL resources owned by one renderer; create/dispose require its current context."""

    def __init__(self, assets: WorldAssets) -> None:
        self.assets: WorldAssets = assets
        self.handles: list[int] = []
        self.textures: list[int] = []
        self.atlas: int = 0
        self.fontchars: tuple[int, ...] | None = None
        self.bitmaps: list[bytes] = []
        self.animated_bitmap_map: list[int] = list(range(256))
        self._palette_textures: dict[int, tuple[int, ...]] = {}
        self._palette_bitmaps: dict[int, tuple[bytes, ...]] = {}
        self._terrain_palettes: dict[int, tuple[bytes, ...]] = {}

    def create(self) -> None:
        """Upload immutable game assets into this renderer texture set."""
        palette = self.assets.palette
        cycles = palette_cycles(palette)
        for index, pixels in enumerate(self.assets.tiles.pixels):
            rgba, animated = indexed_to_rgba(pixels, palette)
            self.textures.append(self._texture(rgba, 16, 16))
            if index < CACHED_TILE_COUNT:
                self.bitmaps.append(indexed_to_rgba(pixels, palette, opaque=True)[0])
            if animated:
                self._palette_textures[index] = tuple(
                    self._texture(indexed_to_rgba(pixels, cycle)[0], 16, 16) for cycle in cycles
                )
                if index < CACHED_TILE_COUNT:
                    self._palette_bitmaps[index] = tuple(
                        indexed_to_rgba(pixels, cycle, opaque=True)[0] for cycle in cycles
                    )
                    if index < BACKGROUND_TILE_COUNT:
                        self._terrain_palettes[index] = self._palette_bitmaps[index]
        self.atlas = self._texture(bytes(256 * 256 * 4), 256, 256)
        for index in range(256):
            self.upload_tile(index, self.bitmaps[index])
        font = self.assets.font
        if font is not None:
            self.fontchars = tuple(
                self._texture(fontchar_to_rgba(font.character(char, transparent=True)), 8, 8)
                for char in range(256)
            )

    def _texture(self, rgba: bytes, width: int, height: int) -> int:
        texture = int(GL.glGenTextures(1))
        self.handles.append(texture)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexImage2D(
            GL.GL_TEXTURE_2D,
            0,
            GL.GL_RGBA,
            width,
            height,
            0,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            rgba,
        )
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameterf(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        return texture

    def upload_tile(self, tile: int, rgba: bytes) -> None:
        """Replace one sixteen-pixel tile in the terrain atlas."""
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.atlas)
        GL.glTexSubImage2D(
            GL.GL_TEXTURE_2D,
            0,
            (tile & 15) * 16,
            tile & ~15,
            16,
            16,
            GL.GL_RGBA,
            GL.GL_UNSIGNED_BYTE,
            rgba,
        )

    def update_palette(self, timer: int) -> None:
        """Select cached palette frames before tile animation is resolved."""
        rotation = timer & 7
        for tile, frames in self._palette_textures.items():
            self.textures[tile] = frames[rotation]
        for tile, frames in self._palette_bitmaps.items():
            self.bitmaps[tile] = frames[rotation]
        for tile, frames in self._terrain_palettes.items():
            self.upload_tile(tile, frames[rotation])

    def update_animation(self, timer: int) -> None:
        """Select object textures and upload animated terrain frames."""
        animation = self.assets.tiles.animations
        for index in range(animation.num_tiles):
            frame = (timer & animation.and_masks[index]) >> animation.shift_values[index]
            destination = animation.tiles[index]
            source = animation.first_frames[index] + frame
            if destination < BACKGROUND_TILE_COUNT:
                if BACKGROUND_TILE_COUNT <= source < CACHED_TILE_COUNT:
                    self.upload_tile(destination, self.bitmaps[source])
                    self.animated_bitmap_map[destination] = source
            else:
                self.textures[destination] = self.textures[source]

    def update_hybrids(self) -> None:
        """Apply byte masks using the currently selected animated source bitmaps."""
        for hybrid in self.assets.tiles.hybrids:
            original = np.frombuffer(self.bitmaps[hybrid.destination], dtype=np.uint8)
            source = np.frombuffer(
                self.bitmaps[self.animated_bitmap_map[hybrid.source]], dtype=np.uint8
            )
            mask = np.frombuffer(hybrid.mask, dtype=np.uint8)
            rgba = np.where(mask, source, original).tobytes()
            self.bitmaps[hybrid.destination] = rgba
            self.upload_tile(hybrid.destination, rgba)

    def dispose(self) -> None:
        """Delete every owned texture handle once in the current Qt context."""
        if self.handles:
            GL.glDeleteTextures(self.handles)
        self.handles.clear()
        self.textures.clear()
        self.atlas = 0
        self.fontchars = None
        self.bitmaps.clear()
        self._palette_textures.clear()
        self._palette_bitmaps.clear()
        self._terrain_palettes.clear()
