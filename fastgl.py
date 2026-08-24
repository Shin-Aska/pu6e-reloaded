"""Python 3 replacement for pu6e's obsolete Python 2 OpenGL extension."""

from OpenGL import GL


def _palette_bytes(palette):
    return palette if isinstance(palette, (bytes, bytearray)) else palette.tobytes()


def indexed_to_rgb(data, palette):
    colors = _palette_bytes(palette)
    return b"".join(colors[index * 3 : index * 3 + 3] for index in data)


def indexed_to_rgba(data, palette):
    """Expand palette indexes and report whether palette animation is needed."""
    colors = _palette_bytes(palette)
    output = bytearray()
    paletted_tile = False
    for index in data:
        output.extend(colors[index * 3 : index * 3 + 3])
        output.append(0 if index == 0xFF else 0xFF)
        paletted_tile |= 0xE0 <= index <= 0xFB
    return bytes(output), int(paletted_tile)


def glTexSubImage2D(*args):
    return GL.glTexSubImage2D(*args)


def draw_poly_maptile(x, y):
    for tx, ty, vx, vy in ((0, 0, x, y), (1, 0, x + 16, y),
                           (1, 1, x + 16, y + 16), (0, 1, x, y + 16)):
        GL.glTexCoord2f(tx, ty)
        GL.glVertex3f(vx, vy, 0)


def draw_poly_maptile_1tex(tile, x, y):
    offset_x, offset_y = tile % 16 / 16.0, tile // 16 / 16.0
    size = 1.0 / 16
    for tx, ty, vx, vy in ((offset_x, offset_y, x, y),
                           (offset_x + size, offset_y, x + 16, y),
                           (offset_x + size, offset_y + size, x + 16, y + 16),
                           (offset_x, offset_y + size, x, y + 16)):
        GL.glTexCoord2f(tx, ty)
        GL.glVertex3f(vx, vy, 0)


def draw_poly_tex(tile, x, y, z):
    GL.glBindTexture(GL.GL_TEXTURE_2D, tile)
    GL.glBegin(GL.GL_QUADS)
    for tx, ty, vx, vy in ((0, 0, x, y), (1, 0, x + 16, y),
                           (1, 1, x + 16, y + 16), (0, 1, x, y + 16)):
        GL.glTexCoord2f(tx, ty)
        GL.glVertex3f(vx, vy, z)
    GL.glEnd()


def draw_chunk(tiles, x, y):
    for row in range(8):
        for column in range(8):
            draw_poly_maptile_1tex(tiles[row * 8 + column], x + column * 16, y + row * 16)


def draw_maptiles(x, y, wx, wy, wz, stride, height, maps, chunks):
    from U6 import Map
    start_x, start_wx = x, wx
    while y < height:
        while x < stride:
            scx, scy, cx, cy, tx, ty = Map.world_to_chunk(wx, wy, wz)
            chunk_width = 16 if wz == 0 else 32
            superchunk = scx + scy * 8
            chunk = maps[superchunk][cx + cy * chunk_width]
            tile = chunks[chunk][tx + ty * 8]
            draw_poly_maptile_1tex(tile, x, y)
            x, wx = x + 16, wx + 1
        x, wx, y, wy = start_x, start_wx, y + 16, wy + 1


def draw_object(texture, status, ox, oy, wx, wy, stride, height):
    """Draw one visible object tile and return zero for legacy compatibility."""
    if ox < wx or oy < wy:
        return 0
    x, y = 16 * (ox - wx), 16 * (oy - wy)
    if x >= stride + 16 or y >= height + 16:
        return 0
    draw_poly_tex(texture, x, y, 0)
    return 0


def _tile_size(tile, tileflags):
    return (tileflags[0x800 + tile] >> 6) & 0x3


def _tile_height(tile, tileflags):
    return (tileflags[0x800 + tile] >> 4) & 0x1


def _draw_object_parts(obj, x, y, draw_height, stride, height, textures, tileflags):
    tile = obj.tile

    def draw(part, part_x, part_y):
        if not (0 <= part_x < stride and 0 <= part_y < height):
            return
        z = _tile_height(part, tileflags)
        if draw_height == z:
            draw_poly_tex(textures[part], part_x, part_y, z)

    # The anchor may be one tile beyond the right/bottom edge for large objects.
    if x < stride + 16 and y < height + 16:
        z = _tile_height(tile, tileflags)
        if draw_height == z:
            draw_poly_tex(textures[tile], x, y, z)
    size = _tile_size(tile, tileflags)
    if size & 2:
        tile -= 1
        draw(tile, x - 16, y)
    if size & 1:
        tile -= 1
        draw(tile, x, y - 16)
        if size & 2:
            tile -= 1
            draw(tile, x - 16, y - 16)


def draw_objblk(block, wx, wy, sx, sy, draw_height, stride, height,
                objblocks, textures, tileflags):
    """Draw an object block in the same painter order as the legacy extension."""
    rows = objblocks[block]
    rows = rows if draw_height == 0 else reversed(rows)
    for oy, row in rows:
        if oy < wy:
            if draw_height == 0:
                break
            continue
        y = sy + 16 * (oy - wy)
        if y >= height + 16:
            if draw_height == 1:
                break
            continue
        points = row if draw_height == 0 else reversed(row)
        for ox, objects in points:
            if ox < wx:
                continue
            x = sx + 16 * (ox - wx)
            if x >= stride + 16:
                continue
            for obj in objects:
                _draw_object_parts(
                    obj, x, y, draw_height, stride, height, textures, tileflags
                )
    return 0
