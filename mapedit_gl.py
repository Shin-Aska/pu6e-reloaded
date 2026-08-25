#!/usr/bin/env python

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import sys
import os
from U6 import tile, pal, look
from U6 import Map, obj, book, NPCs, Font, Config
from array import array
from contextlib import chdir
from struct import pack
# import pygame
# from Image import *
import fastgl
import numpy as Numeric

TILE_WIDTH = 16
TILE_HEIGHT = 16
TILES_X = 16

palette = None
bitmaps  = None
# Map bitmap tile to animated tile number: used so hybrid tile can find
# the right source bitmap, since we don't update the actual bitmap data.
animated_bitmap_map = [0] * 256
initialized = 0
frames = 0
frames_to_display = 0   # Display this many frames, then quit.
display_grid = 0
display_objects = 1
display_coords = 1
fullscreen = 0
animate_tiles = 1
rotate_palette = 1
hybrid_tiles = 0
draw_npcs_separately = 0
fade_objects = 0.0
game_timer = 0
paletted = {}
coords = [0xde, 0xad, 0]
center_offset = (0, 0)

fontchars = None
def screen_to_world(x, y):
	wx, wy, wz = coords
	if wz == 0:
		world_width = 1024
	else:
		world_width = 256

	return ((wx + int(x / 16.0 / scale_factor)) % world_width,
	        (wy + int(y / 16.0 / scale_factor)) % world_width,
			 wz)

def wrap_coords(wx, wy, wz):
	if wz == 0:
		world_width = 1024
	else:
		world_width = 256
	return wx % world_width, wy % world_width, wz % 6

def get_centered_coords():
	return wrap_coords(coords[0] + center_offset[0],
	                   coords[1] + center_offset[1],
		               coords[2])

def set_centered_coords(wx, wy, wz):
	global coords
	xo, yo = center_offset
	coords = wrap_coords(wx - xo, wy - yo, wz)

def indexed_to_rgbx(data):
	rgb = []
	p = palette.pal
	for i in data:
		rgb.extend(p[i])
		rgb.append(255)
	return Numeric.array(rgb, Numeric.uint8)

def indexed_to_rgba(data, p):
	rgb = []
	p = palette.pal
	paletted_tile = 0
	for i in data:
		i = i if isinstance(i, int) else ord(i)
		rgb.extend(p[i])
		if i == 255:
			rgb.append(0)
		else:
			rgb.append(255)
		if 0xE0 <= i <= 0xFB:
			paletted_tile = 1   # This tile contains a rotated palette entry.
	return array('B', rgb).tobytes(), paletted_tile

def indexed_to_rgba_2(data, p):
	rgb = array('B')
	paletted_tile = 0
	for i in data:
		i = i if isinstance(i, int) else ord(i)
		rgb.fromlist(list(p[i]))
		if i == 255:
			rgb.append(0)
		else:
			rgb.append(255)
		if 0xE0 <= i <= 0xFB:
			paletted_tile = 1   # This tile contains a rotated palette entry.
	return rgb.tobytes(), paletted_tile

indexed_to_rgba = fastgl.indexed_to_rgba
glTexSubImage2D = fastgl.glTexSubImage2D   # Use the buffer interface.

def maptile_to_texture(num):
	global paletted   # paletted tile dictionary
	# palette.palstr = palette.pal    # This is here for the old indexed_to_rgba code, which
	                                  # takes a list rather than a palette string.
	data, paletted_tile = indexed_to_rgba(tile.maptiles[num], palette.palstr)
	if paletted_tile:
		# paletted must be an empty dict on the first run-through.
		# We're later called when populating the paletted array with tile data,
		# so we don't want to destroy it if the key already exists.
		if num not in paletted:
			paletted[num] = []
	ix = iy = 16

	tex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, tex)

	glPixelStorei(GL_UNPACK_ALIGNMENT,1)  # FIXME necessary?
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, ix, iy, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
#	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_DECAL)
	return tex

# Generate a 16x16 (256-tile) maptile texture from tile RGB data.  We could
# also generate from pre-created tile textures.
def generate_map_texture():

	# Create the map texture
	tex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, tex)
	glPixelStorei(GL_UNPACK_ALIGNMENT,1)
	# Can I create an empty texture without source data?
	glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 256, 256, 0, GL_RGBA, GL_UNSIGNED_BYTE, "\0" * 256 * 256 * 4)
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
	# Scaled-down textures use linear filter, which looks nicer.
	glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)

	x = 0
	y = 0
	for num in range(256):
		data = indexed_to_rgbx(tile.maptiles[num])
		glTexSubImage2D(GL_TEXTURE_2D, 0, x*16, y*16, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, data)
		x += 1
		if x >= 16: x = 0; y += 1

	return tex

def fontchar_to_rgba(fontchar_pal):
	"""Convert an 8x8 font mask to 64 native RGBA pixels."""
	rgba = Numeric.zeros(64, dtype=Numeric.uint32)
	white = Numeric.full(64, 0xFFFFFFFF, dtype=Numeric.uint32)
	Numeric.putmask(rgba, fontchar_pal, white)
	return rgba.tobytes()

def InitGL(w, h):
	global textures
	global maptex, fonttex
	global bitmaps
	global paletted
	global fontchars

	print("Converting tiles to textures...")

	# FIXME!! I don't need the first 256 of these, at least, since they're in the map texture.
	paletted = {}   # maptile_to_texture will populate this dictionary with indices of paletted tiles
	palette.palstr = palette.tobytes()  # Set palstr, used by maptile_to_texture.
	textures = [ maptile_to_texture(i) for i in range(2048) ] # all tiles

	print("Generating paletted textures...")
	# Generate 8 textures for each paletted texture, one for each possible rotation.
	# We waste space because some tiles will be identical (the 4-entry ones).
	# The palette will rotate fully and wind up as it started.
	for r in range(8):
		for k, v in paletted.items():
			if k < 256:
				v.append(indexed_to_rgbx(tile.maptiles[k]))
			else:
				v.append(maptile_to_texture(k))
		palette.rotate(8, 0xE0, 0xE8)
		if r & 1:
			palette.rotate(4, 0xF0, 0xF4, 0xF8)
		palette.palstr = palette.tobytes()   # Make sure to refresh palstr here.

	print("Generating map texture...")
	maptex = generate_map_texture()

	print("Generating animated bitmap cache...")
	# Bitmap cache -- temporary for now, for animated tiles
	bitmaps = [ indexed_to_rgbx(tile.maptiles[i]) for i in range(0,512) ]

	update_animated_tiles(0)

	fontchars = None
	if Font.chardata is not None:
		print("Generating font texture...")
		fontchars = glGenTextures(256)
		for i in range(256):
			fontchar_pal = Font.convert_1_to_8(i, 1)
			# fontchar_rgba, dummy = indexed_to_rgba(fontchar_pal, palette.palstr)
			fontchar_rgba = fontchar_to_rgba(fontchar_pal)
			glBindTexture(GL_TEXTURE_2D, fontchars[i])
			glPixelStorei(GL_UNPACK_ALIGNMENT,1)  # FIXME necessary?
			glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 8, 8, 0, GL_RGBA, GL_UNSIGNED_BYTE, fontchar_rgba)
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)

	glEnable(GL_TEXTURE_2D)
	glClearColor(0.0, 0.0, 0.0, 0.0)	# clear bg to black (not used)
	glClearDepth(1.0)					# clear depth buffer
	glDepthFunc(GL_LEQUAL)				# Important: set depth function so that the last object
	                                    #   drawn at a given depth will be the one displayed.
	glEnable(GL_DEPTH_TEST)
	glShadeModel(GL_FLAT)
	glAlphaFunc(GL_GREATER, 0.01)

	Resize(w, h)

def Resize(w, h):
	global screen_width, screen_height, center_offset
	glViewport(0, 0, w, h)
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glOrtho(0, w/scale_factor, h/scale_factor, 0, -100, 100)  # scale up by scale_factor
	glMatrixMode(GL_MODELVIEW)

	old_center = get_centered_coords()
	screen_width, screen_height = w, h
	center_offset = int(w / scale_factor / 16 / 2), int(h / scale_factor / 16 / 2)
	set_centered_coords(*old_center)

# 300 frames: 6.6s no dummy, 7.6s 1 dummy, 13.4s 8 dummy,
#             30s rendering w/ bind-per-tile
#             20s rendering w/ bind-per-tile (vertex drawing in fastgl C module)
#             19s full rendering w/o bind-per-tile,
#             10s rendering w/o bind-per-tile + fastgl
# I can get 24 fps at 1280x1024 full screen.
def draw_map():
	global fade_objects

	width = int(screen_width / scale_factor)
	height = int(screen_height / scale_factor)

	stride = width & ~15
	if width & 15:
		stride += 16

	glDisable(GL_DEPTH_TEST)
	glDisable(GL_BLEND)
	glDisable(GL_ALPHA_TEST)  # You can now enable this with no problem.
	glEnable(GL_TEXTURE_2D)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
	glBindTexture(GL_TEXTURE_2D, maptex)

	scxs, scys, cxs, cys, txs, tys = Map.world_to_chunk(*coords)
	xs, ys = 0, 0

	wx, wy, wz = coords
	wxs = wx

	m = Map.map
	c = Map.chunks

	if wz == 0:
		cw = ch = 16    # set chunk width / height based on level
	else:
		cw = ch = 32

	if 1:
		fastgl.draw_maptiles(xs, ys, wx, wy, wz, stride, height, m, c)
	elif 0:
		# Python version of draw_maptiles
		x, y = xs, ys
		# scx, scy, cx, cy, tx, ty = scxs, scys, cxs, cys, txs, tys
		w_to_c = Map.world_to_chunk

		while y < height:
			while x < stride:
				scx, scy, cx, cy, tx, ty = w_to_c(wx, wy, wz)

				schunk = scx + scy * 8   # 8x8 superchunks / map
				chunk = m[schunk][cx + cy * cw]     # 16x16 chunks / schunk
				t  = c[chunk][tx + ty * 8]    # 8x8 tiles / chunk
				fastgl.draw_poly_maptile_1tex(t, x, y)
				# Next column
				x += 16 # tile width
				wx += 1
			# Next row
			x = xs; wx = wxs
			y += 16
			wy += 1
	elif 1:
		# This section draws the map by chunks.  The C version (draw_chunk) is somewhat slower
		# than the draw_maptiles C version used above.   However, the python version here
		# is faster than that above by about 2x.
		wx, wy, wz = coords
		wxs = wx
		xs = -(txs * 16)
		ys = -(tys * 16)
		x = xs
		y = ys
		chunks = []
		# Build a list of chunk numbers and coordinates to draw them at
		while y < height:
			while x < stride:
				chunk = Map.world_to_chunk_num(wx, wy, wz)[0]
				chunks.append((chunk, x, y))
				x  += 128
				wx +=   8
			x = xs
			wx = wxs
			y  += 128
			wy +=   8

		if 0:
			# draw chunk -- python
			for chk, x, y in chunks:
				tiles = c[chk]
				for j in range(0, 64, 8):
					for i in range(8):
						t = tiles[i + j]
						fastgl.draw_poly_maptile_1tex(t, x, y)
						x += 16
					x -= 128
					y += 16
		elif 1:
			# draw chunk -- C
			for chk, x, y in chunks:
				fastgl.draw_chunk(c[chk], x, y)

	wx, wy, wz = coords

	if display_grid:
		draw_grid(width, height, txs, tys)

	glEnable(GL_TEXTURE_2D)
	glEnable(GL_ALPHA_TEST)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glColor4f(1.0, 1.0, 1.0, 1.0)

	if display_objects or fade_objects >= 0.0:
#		glEnable(GL_DEPTH_TEST)
		if fade_objects >= 0.0:
			glColor4f(1.0, 1.0, 1.0, fade_objects)
			fade_objects -= 0.33

		s = os = scxs + scys * 8
		blocks = []

		# Calculate which superchunks are visible by performing a dry run
		# [and deposit them in 'blocks'].
		y = -(tys * 16 + cys * 16 * 8)
		x = xs = -(txs * 16 + cxs * 16 * 8)
		wxs = wx

		while y < height:
			while x < stride:
				s = obj.world_to_block(wx, wy, wz)
				blocks.append((s, x, y))
				x  += 128 * cw
				wx +=   8 * cw
			x = xs
			wx = wxs
			y  += 128 * ch
			wy +=   8 * ch

		blocks.reverse()   # Superchunks should be drawn in reverse order (at height 0, at least)
		wx, wy, wz = coords   # restore coordinates

		# The fastgl version does speed us up noticeably, at the cost of
		# obscurity.  I believe the object attribute lookups are still
		# slowing us down.
		# 2000 frames: 75 sec 1024x768x1 @ (0x134,16c)    [python version: 86 sec]
		#              56 sec scrolling (because fewer objects)
		#              56 sec maptiles only.
		#  includes ~8-9 sec startup time.
		# Using the array references to obj (rather than dict) saves another
		# 9 or 10 seconds.  However, dict references become -extremely- expensive
		# when the pseudohash is in use.  Times after this point use the array.
		#              75 s with depth enabled [101s python version]
		#              78 s with animation + depth.
		#              49 s with all + draw_maptiles C code [improves higher
		#                   resolutions substantially].  [Hmm, now I'm getting 54s.]

		# 98 s: 200 frames at scale factor 1/8, fast maptiles, slow objects
		# 48 s: 200 frames at scale factor 1/8, fast maptiles, fast objects
		# 330s: 200 frames at scale factor 1/8, slow maptiles, fast objects

		if 0:
			fastgl.draw_objects(blocks, obj.objblk, textures, tile.tileflag, wx, wy, stride, height)
		elif 0:
			# This is fastgl.draw_objects written in Python.
			for block in blocks:
				for o in obj.objblk[block]:
					# This inner loop is the slow part.
					# if o.status & 0xF6: continue
					if o.x < wx: continue
					if o.y < wy: continue

	#				# FIXME this will not wrap correctly.
					x = 16 * (o.x - wx)
					if x >= stride + 16: continue
					y = 16 * (o.y - wy)
					if y >= height + 16: continue

					t = o.tile
					h = tile.height(t)   # Height is a boolean value.
					fastgl.draw_poly_tex(textures[t], x, y, h)

					# Draw large objects (size > 1 tile).  # When this section is enabled, drawing time increases
					# from 86 to 97 seconds (see stats above), 101 with depth.

					size = tile.size(t)  # Size will be a 2-bit value.
					if size & 2:   # Width 2: lower left
						t -= 1
						if x - 16 < stride and y < height and x - 16 >= 0:
							h = tile.height(t)
							fastgl.draw_poly_tex(textures[t], x - 16, y, h)
					if size & 1:   # Height 2: upper right
						t -= 1
						if x < stride and y - 16 < height and y - 16 >= 0:
							h = tile.height(t)
							fastgl.draw_poly_tex(textures[t], x, y - 16, h)
						if size & 2:  # Width 2: upper left
							t -= 1
							if x - 16 < stride and y - 16 < height and x - 16 >= 0 and y - 16 >= 0:
								h = tile.height(t)
								fastgl.draw_poly_tex(textures[t], x - 16, y - 16, h)
		elif 0:
			for dh in (0,1):
				# dh is draw height; dir is draw direction (se-nw=1 or nw-se=-1).
				if dh == 1:
					blocks.reverse()  # Reverse the order of the superchunks (again)
				for block in blocks:
					# print "block %d len %d" % (block, len(obj.objblk[block]))
				# Warning: blocks should also be in drawing (se-nw or nw-se order)
					# Two passes: forward through list (se-nw, height 0) then reverse (nw-se, hgt. 1)
					if dh == 1:
						rows = obj.objblk[block][:]
						rows.reverse()
					else:
						rows = obj.objblk[block]

					for oy, row in rows:
						if oy < wy:
							# Stop once we get off the screen vertically (depending on which
							# direction we're going--see the opposite test below).
							# This doesn't seem to buy us that much time.
							if dh: continue
							else: break

						y = 16 * (oy - wy)     # FIXME This still doesn't wrap correctly.
						if y >= height + 16:   # The +16 lets us draw offscreen double height tiles
							if not dh: continue
							else: break

						if dh == 1:
							row = row[:]       # Copy row: so we don't have to reverse it again
							row.reverse()

						for ox, point in row:
							if ox < wx: continue
							x = 16 * (ox - wx)    # FIXME This still doesn't wrap correctly.
							if x >= stride + 16: continue

							for o in point:

								t = o.tile
								h = tile.height(t)   # Height is a boolean value.
								if dh == h: fastgl.draw_poly_tex(textures[t], x, y, h)

								# Draw large objects (size > 1 tile).
								# When this section is enabled, drawing time increases
								# from 86 to 97 seconds (see stats above), 101 with depth.

								size = tile.size(t)  # Size will be a 2-bit value.
								if size & 2:   # Width 2: lower left
									t -= 1
									if x - 16 < stride and y < height and x - 16 >= 0:
										h = tile.height(t)
										if dh == h: fastgl.draw_poly_tex(textures[t], x - 16, y, h)
								if size & 1:   # Height 2: upper right
									t -= 1
									if x < stride and y - 16 < height and y - 16 >= 0:
										h = tile.height(t)
										if dh == h: fastgl.draw_poly_tex(textures[t], x, y - 16, h)
									if size & 2:  # Width 2: upper left
										t -= 1
										if x - 16 < stride and y - 16 < height and x - 16 >= 0 and y - 16 >= 0:
											h = tile.height(t)
											if dh == h: fastgl.draw_poly_tex(textures[t], x - 16, y - 16, h)
		elif 0:
			draw_objects(blocks, stride, height)
		elif 1:
			draw_fastgl_objects(blocks, stride, height)

	if display_coords:
		draw_coords()

def draw_objects(blocks, stride, height):
	for block, sx, sy in blocks:
		draw_objblk(block, sx, sy, 0, stride, height)
	blocks.reverse()
	for block, sx, sy in blocks:
		draw_objblk(block, sx, sy, 1, stride, height)

def draw_fastgl_objects(blocks, stride, height):
	# This should be done by draw_objects, but fastgl.draw_objblk needs extra
	# arguments.
	for block, sx, sy in blocks:
		wx, wy, wz = obj.block_to_world(block)   # Coordinates of upper-left tile.
		fastgl.draw_objblk(block, wx, wy, sx, sy, 0, stride, height, obj.objblk, textures, tile.tileflag)
	blocks.reverse()
	for block, sx, sy in blocks:
		wx, wy, wz = obj.block_to_world(block)   # Coordinates of upper-left tile.
		fastgl.draw_objblk(block, wx, wy, sx, sy, 1, stride, height, obj.objblk, textures, tile.tileflag)

# dh: draw_height (0 or 1)
# sx, sy: screen coordinates of the block
def draw_objblk(block, sx, sy, dh, stride, height):
	wx, wy, wz = obj.block_to_world(block)   # Coordinates of upper-left tile.

	if dh == 1:
		rows = obj.objblk[block][:]
		rows.reverse()
	else:
		rows = obj.objblk[block]

	for oy, row in rows:
		if oy < wy:   # FIXME this will probably not wrap correctly
			# Stop once we get off the screen vertically (depending on which
			# direction we're going--see the opposite test below).
			# This doesn't seem to buy us that much time.
			if dh: continue
			else: break

		y = sy + 16 * (oy - wy)
		if y >= height + 16:   # The +16 lets us draw offscreen double height tiles
			if not dh: continue
			else: break

		if dh == 1:
			row = row[:]       # Copy row: so we don't have to reverse it again
			row.reverse()

		for ox, point in row:
			if ox < wx: continue
			x = sx + 16 * (ox - wx)
			if x >= stride + 16: continue

			for o in point:

				t = o.tile
				h = tile.height(t)   # Height is a boolean value.
				if dh == h: fastgl.draw_poly_tex(textures[t], x, y, h)

				# Draw large objects (size > 1 tile).
				# When this section is enabled, drawing time increases
				# from 86 to 97 seconds (see stats above), 101 with depth.

				size = tile.size(t)  # Size will be a 2-bit value.
				if size & 2:   # Width 2: lower left
					t -= 1
					if x - 16 < stride and y < height and x - 16 >= 0:
						h = tile.height(t)
						if dh == h: fastgl.draw_poly_tex(textures[t], x - 16, y, h)
				if size & 1:   # Height 2: upper right
					t -= 1
					if x < stride and y - 16 < height and y - 16 >= 0:
						h = tile.height(t)
						if dh == h: fastgl.draw_poly_tex(textures[t], x, y - 16, h)
					if size & 2:  # Width 2: upper left
						t -= 1
						if x - 16 < stride and y - 16 < height and x - 16 >= 0 and y - 16 >= 0:
							h = tile.height(t)
							if dh == h: fastgl.draw_poly_tex(textures[t], x - 16, y - 16, h)



# Draw a grid showing accurate chunk boundaries.
def draw_grid(width, height, txs, tys):
	# Draw grid
	glDisable(GL_TEXTURE_2D)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glBegin(GL_QUADS)
	glColor4f(1.0, 0.8, 0.7, 0.6)
	# The "width + 128" part is so I get borders on the right and bottom of the screen.
	xs = -(txs * 16)
	ys = -(tys * 16)
	xvals = list(range(xs, width + 128, 128))
	yvals = list(range(ys, height + 128, 128))
	for x in xvals:
		glVertex3f(x-1,0,1)
		glVertex3f(x+1,0,1)
		glVertex3f(x+1,height,1)
		glVertex3f(x-1,height,1)
	for y in yvals:
		glVertex3f(0,y-1,1)
		glVertex3f(width,y-1,1)
		glVertex3f(width,y+1,1)
		glVertex3f(0,y+1,1)
	glEnd()


	# Draw chunk numbers
	# but don't draw them if we have no font!
	if fontchars is None: return

	# glScalef(0.5, 0.5, 1.0)
	glEnable(GL_TEXTURE_2D)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)

	wx, wy, wz = coords
	wxs = wx
	x = xs
	y = ys
	chunks = []
	while y < height:
		while x < width:
			chunk = Map.world_to_chunk_num(wx, wy, wz)[0]
			chunks.append((chunk, x, y))
			x  += 128
			wx +=   8
		x = xs
		wx = wxs
		y  += 128
		wy +=   8

	#r, g, b = palette.pal[Font.transparent]
	#r, g, b = r / 256.0, g / 256.0, b / 256.0
	for c, x, y in chunks:
		glColor4f(0, 0, 0, 0.7)
		draw_font_str("%s" % c, x+21, y+21, 0)
		glColor4f(1.0, 0.8, 0.8, 0.8)   # Can't get glColor4b to work (?!)
		draw_font_str("%s" % c, x+20, y+20, 0)

def draw_coords():
	if fontchars is None: return
	width = int(screen_width)
	height = int(screen_height)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
	glMatrixMode(GL_PROJECTION)
	glPushMatrix()
	glLoadIdentity()
	glOrtho(0, width, height, 0, -100, 100)  # Fixed scaling.

	x = width - 200
	y = 20
	draw_text_bg(x - 5, y - 5, 9*16 + 10, 16 + 10)
	glEnable(GL_TEXTURE_2D)
	glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
	glColor4f(0, 0, 0, 0.7)
	crd = get_centered_coords()
	draw_font_str("%03x %03x %d" % crd, x+1, y+1, 0)
	r, g, b = palette.pal[Font.on]
	glColor4f(r/255.0, g/255.0, b/255.0, 1.0)   # Can't get glColor4b to work (?!)
	#glColor4f(0.8, 0.8, 1.0, 1.0)
	draw_font_str("%03x %03x %d" % crd, x, y, 0)
	glPopMatrix()
	glMatrixMode(GL_MODELVIEW)

def dummy(): pass

def draw():
	global frames

	if frames_to_display and frames > frames_to_display: sys.exit()

	# Framerate is improved without the depth buffer
	# (well, maybe not -- small improvement (1.5 fps) for each fewer clear operation)
#	glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
#	glClear(GL_DEPTH_BUFFER_BIT)
	glLoadIdentity()					# Reset The View

	# Palette updates come first so updated palette is propagated to animated tiles this frame.
	# Otherwise, they're delayed one frame.
	if rotate_palette:
		update_paletted_tiles(game_timer)
	if animate_tiles:
		if Config.gametype != 'md':
			# Don't bother animating the MD canals, saving us an epileptic attack.
			# This needs to be generified, because there are certain tiles in U6
			# that should only be animated at certain times (cranks, bells, ...)
			update_animated_tiles(game_timer)
	if hybrid_tiles:
		update_hybrid_tiles(game_timer)

#	coords[0] += 1
#	coords[0] &= 1023
#	coords[1] &= 1023

	draw_map()
#	draw_font_test()
	frames += 1

def draw_font_str(str, x, y, z):
	for c in str:
		c = ord(c)
		draw_font_char(c, x, y, z)
		x += 16

def draw_font_char(char, x, y, z):
	fastgl.draw_poly_tex(fontchars[char], x, y, z)

def draw_text_bg(x, y, w, h):
	glDisable(GL_TEXTURE_2D)
	glBegin(GL_QUADS)
	r, g, b = palette.pal[Font.off]
	glColor4f(r/255.0, g/255.0, b/255.0, 0.8)
	glVertex3f(x, y,  0)
	glVertex3f(x+w, y,  0)
	glVertex3f(x+w,  y+h,  0)
	glVertex3f(x, y+h,  0)
	glEnd()

def draw_font_test():
	# FIXME font testing
	# Draw translucent background
	glDisable(GL_TEXTURE_2D)
	glBegin(GL_QUADS)
	x, y = 10, 10
	w, h = 150, 60
	draw_text_bg(x, y, w, h)

	glScalef(0.5, 0.5, 1.0)   # warning: matrix not saved
	glEnable(GL_TEXTURE_2D)
	r, g, b = palette.pal[Font.transparent]
	glColor4f(r/255.0, g/255.0, b/255.0, 1.0)   # Can't get glColor4b to work (?!)
	draw_font_str("hello, this is jim", x+21, y+21, 0)
	r, g, b = palette.pal[Font.on]
	glColor4f(r/255.0, g/255.0, b/255.0, 1.0)   # Can't get glColor4b to work (?!)
	draw_font_str("hello, this is jim", x+20, y+20, 0)


def tick():
	global game_timer
	game_timer += 1

def draw_glut():
	tick()	# Animate one frame
	draw()
	glutSwapBuffers()

def draw_maptiles():
	tex = 0
	for y in range(0, 1024, 16):
		for x in range(0, 512, 16):
			glBindTexture(GL_TEXTURE_2D, textures[tex])
			glBegin(GL_QUADS)
			glTexCoord2f(0, 0); glVertex3f(x, y,  0)
			glTexCoord2f(1, 0); glVertex3f(x+16, y,  0)
			glTexCoord2f(1, 1); glVertex3f(x+16,  y+16,  0)
			glTexCoord2f(0, 1); glVertex3f(x, y+16,  0)
			glEnd()
			tex += 1

# This is, at first testing, about 2.2x faster than binding texture/translating every time.
def draw_maptiles_1tex():
	glBindTexture(GL_TEXTURE_2D, textures[0])
	glBegin(GL_QUADS)
	for y in range(0, 1024, 16):
		for x in range(0,512,16):
			glTexCoord2f(0, 0); glVertex3f(  x, y,  0)
			glTexCoord2f(1, 0); glVertex3f( x+16, y,  0)
			glTexCoord2f(1, 1); glVertex3f( x+16, y+16,  0)
			glTexCoord2f(0, 1); glVertex3f(x,  y+16,  0)
	glEnd()

def init(w, h):
	global window
	glutInit(sys.argv)

	glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)

	glutInitWindowSize(w, h)
	glutInitWindowPosition(0, 0)
	window = glutCreateWindow("Map Editor (GL)")

	glutDisplayFunc(draw_glut)
	glutIdleFunc(draw_glut)
	glutReshapeFunc(Resize)
	glutKeyboardFunc(keyPressed)

	# glutFullScreen()
	# Initialize our window.
	InitGL(w, h)
	#sys.exit()

	# Start Event Processing Engine
	glutMainLoop()

def keyPressed(key, x, y):
	global display_grid, display_objects, hybrid_tiles
	global fade_objects
	global scale_factor, game_timer
	key = key.upper()
	if key == 'Q':
		print("frames: %d" % frames)
		sys.exit()
	if key == 'G':
		display_grid ^= 1
	if key == '=':
		scale_factor *= 2.0
		Resize(screen_width, screen_height)  # can I trigger a resize event?
	if key == '-':
		scale_factor /= 2.0
		Resize(screen_width, screen_height)  # can I trigger a resize event?
	if key == 'A':
		# animate one frame
		game_timer += 1
		update_animated_tiles(game_timer)
	if key == 'O':
		display_objects ^= 1
		if display_objects == 0: fade_objects = 1.0
	if key == 'H':
		hybrid_tiles ^= 1

def update_animated_tiles(game_timer):
	global textures
	global animated_bitmap_map

	anim = tile.anim
	# Kludge: bind the maptex texture only once: if we write to other textures,
	# we'll need to bind them.
	glBindTexture(GL_TEXTURE_2D, maptex)

	for i in range(anim['numtiles']):
		frame_num = (game_timer & anim['and_masks'][i]) >> anim['shift_values'][i];
		t = anim['tiles'][i];
		f = anim['first_frame'][i] + frame_num;
#		print "animating tile %d: with frame %d" % (t, f)
		if t < 256:
			# Destination tile is in the map texture.
			# Currently, we cache raw data from tiles 256-511 in bitmaps[0..255];
			# recalculating is -very- slow.
			# We should probably copy from a texture, instead; we could
			# create textures for the animated tiles on the fly, if desired.
			# We could also have each tile go through a lookup table.
			if 256 <= f < 512:   # Just in case, though this test should never fail.
				x = (t & 15) << 4
				y = (t & ~15)
				#dummy()
				glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, bitmaps[f])
				animated_bitmap_map[t] = f
		else:
			# Destination tile is an object (512-2047).  Source tile
			# is always from tiles 256-511 as above, but this doesn't matter currently.
			# We just update the texture number of the destination tile.
			textures[t] = textures[f]

# This is substantially slower
def update_animated_tiles_copy(game_timer):
	global textures
	anim = tile.anim
#	glBindTexture(GL_TEXTURE_2D, maptex)
	fastgl.draw_poly_tex(maptex, 0, 0, 0)

	for i in range(anim['numtiles']):
		frame_num = (game_timer & anim['and_masks'][i]) >> anim['shift_values'][i];
		t = anim['tiles'][i];
		f = anim['first_frame'][i] + frame_num;
#		print "animating tile %d: with frame %d" % (t, f)
		if t < 256:
			# Destination tile is in the map texture.
			# Currently, we cache raw data from tiles 256-511 in bitmaps[0..255];
			# recalculating is -very- slow.
			# We should probably copy from a texture, instead; we could
			# create textures for the animated tiles on the fly, if desired.
			# We could also have each tile go through a lookup table.
			if 256 <= f < 512:   # Just in case, though this test should never fail.
				x = (t & 15) << 4
				y = (t & ~15)
				#dummy()
				fastgl.draw_poly_tex(textures[t], x, y, 0)
#				glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, bitmaps[f])
		else:
			# Destination tile is an object (512-2047).  Source tile
			# is always from tiles 256-511 as above, but this doesn't matter currently.
			# We just update the texture number of the destination tile.
			textures[t] = textures[f]

	glBindTexture(GL_TEXTURE_2D, maptex)
	glCopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, 64, 16)

# Update texture numbers from the paletted dict.
def update_paletted_tiles(game_timer):
	global textures
	glBindTexture(GL_TEXTURE_2D, maptex)

	r = game_timer & 7          # take the lower 3 bits, 0-7
	for k, v in paletted.items():
		if k < 256:
			x = (k & 15) << 4
			y = (k & ~15)
			glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, v[r])
		else:
			textures[k] = v[r]

def update_hybrid_tiles(game_timer):
	glBindTexture(GL_TEXTURE_2D, maptex)

	# This is slow (~16% CPU)
	for (dest, src, mask) in tile.hybrids:
		Numeric.putmask(bitmaps[dest], mask, bitmaps[animated_bitmap_map[src]])
		x = (dest & 15) << 4
		y = (dest & ~15)    # this part really needs to become a function!
		glTexSubImage2D(GL_TEXTURE_2D, 0, x, y, 16, 16, GL_RGBA, GL_UNSIGNED_BYTE, bitmaps[dest])

def read_data(directory, game='fp'):
	global palette
	Config.gamedir = os.path.abspath(directory)
	Config.gametype = game
	with chdir(Config.gamedir):
		palette = pal.pal()
		palette.read(game)   # palette, look, Font and book currently require gametype
		book.read(game)
		look.read(game)
		tile.read()
		Map.read()
		obj.read()
		NPCs.read()
		NPCs.populate()
		#  the NPC frame will not be correct because .tile only takes .type into consideration
		Font.read(game)

if __name__ == '__main__':
	global screen_width, screen_height, scale_factor

	print("Reading data files...")
	Config.read('pu6e.conf')
	read_data(Config.gamedir, Config.gametype)

	set_centered_coords(0x134, 0x16c, 0)
#	coords = [0x20, 0x20, 1]
	scale_factor = 1
	w, h = 1024, 768
	init(w, h)
