#!/usr/bin/env python

import re
import os
from struct import unpack, pack
from array import array
from U6.util import file_backup
from U6 import Config

default_fn = { 'chunks': "chunks",
               'map':    "map"
}
map = []
chunks = []
chunks_dirty = 0
map_dirty = 0

def read(fn=default_fn):
	parse_chunks(open(fn['chunks'], 'rb'))
	parse_map(open(fn['map'], 'rb'))

def write_chunks(fn=default_fn):
	global chunks_dirty
	name = fn['chunks']
	name = os.path.join(Config.gamedir, name)
	file_backup(name)
	f = open(name, 'wb')
	for chunk in chunks:
		f.write(array('B', chunk).tobytes())
	chunks_dirty = 0

def write_map(fn=default_fn):
	global map_dirty
	name = fn['map']
	name = os.path.join(Config.gamedir, name)
	file_backup(name)
	f = open(name, 'wb')

	if len(map) != 69:
		raise ValueError("map data structure is %d instead of 69 blocks long" % len(map))

	for schk in map:
		for t in range(0, len(schk), 2):
			t1 = schk[t]
			t2 = schk[t+1]
			b0 = t1 & 0xFF
			b1 = (t1 >> 8 & 0xF) | (t2 << 4 & 0xF0)
			b2 = t2 >> 4
			str = pack("3B", b0, b1, b2)
			f.write(str)

	map_dirty = 0

def parse_chunks(f):
	global chunks
	chunks = []
	chunks_dirty = 0

	while 1:
		chunk = f.read(64)
		if not chunk: break
		chunks.append(list(unpack("64B", chunk)))

# Unequivocally write out data structures.
def write(fn=default_fn):
	chunks_dirty = 1
	write_changes(fn)

def write_changes(fn=default_fn):
	if chunks_dirty:
		write_chunks(fn)
	if map_dirty:
		write_map(fn)

# map format: 3 nibbles (little-endian) == chunk #
# surface superchunk = 16x16 chunk #s
# dungeon superchunk = 32x32 chunk #s
# map: 8x8 superchunks + 5 dungeon superchunks == 32256 bytes
def parse_map(f):
	global map
	map = []

	while len(map) < 64:
		schk = []
		while len(schk) < 16*16:
			buf = f.read(3)
			# Obtain 2 chunk #s from 3 bytes (6 nibbles)
			bytes = unpack("3B", buf)
			schk.append(((bytes[1] & 0xF) << 8) | bytes[0])
			schk.append((bytes[2] << 4) | (bytes[1] >> 4))
		map.append(schk)

	# The last five entries (64-68) are the dungeon schunks.
	while len(map) < 69:
		schk = []
		while len(schk) < 32*32:
			buf = f.read(3)
			# Obtain 2 chunk #s from 3 bytes (6 nibbles).
			# Format identical to surface superchunks.
			bytes = unpack("3B", buf)
			schk.append(((bytes[1] & 0xF) << 8) | bytes[0])
			schk.append((bytes[2] << 4) | (bytes[1] >> 4))
		map.append(schk)

# Since dungeons are 4 times smaller than surface in both
# directions, we have to map src to dest chunks when
# travelling to and from the surface.
def adjust_coords_for_level(wx, wy, wz, newz, quality=0):
	newz = newz % 6   # In case caller didn't wrap.
	if wz == 0 and newz > 0:   # Moving down from surface.
		wx, wy = _down(wx), _down(wy)
	elif wz > 0 and newz == 0:  # Moving up to surface.
		# The lower 4 bits of quality determine which of 16 possible
		# chunks we ascend to.  Bits 3,2 = y offset; bits 1,0 = x offset.
		xoff = quality      & 0x03
		yoff = quality >> 2 & 0x03
		wx, wy = _up(wx, xoff), _up(wy, yoff)
	return wx, wy, newz

# Helpers for adjust_coords_for_level
def _down(x):
	# 4x4 chunks are reduced to 1 by dropping bits 3 and 4.
	# You'll appear at the same tile as you were in the source chunk.
	return ((x & 0x07) | (x >> 2 & 0xF8))
def _up(x, offset=0):
	# 1 chunk can map to any of 4x4 chunks on the surface.
	# The offset determines which of the 4 chunks (in one direction)
	# we select.
	return ((x & 0x07) | (x << 2 & 0x3E0) | (offset << 2 & 0x0C))


# Convert (superchunk-x, schunk-y, chunk-x, chunk-y, tile-x, tile-y) coordinates to (world-x, world-y).
def chunk_to_world(scx, scy, cx, cy, tx, ty):
	raise NotImplementedError("chunk_to_world does not handle z values")
	return(scx * 128 + cx * 8 + tx,
	       scy * 128 + cy * 8 + ty)

# Convert (world-x, world-y, world-z) to (superchunk-x, schunk-y, chunk-x, chunk-y, tile-x, tile-y).
# Surface world coordinates are taken mod 1024 (and dungeon mod 256) so
# you don't have to wrap, though # it's probably required elsewhere.
def world_to_chunk(x, y, z):
	if z == 0:
		return(x >> 7 & 0x7, y >> 7 & 0x7,
			   x >> 3 & 0xF, y >> 3 & 0xF,
			   x      & 0x7, y      & 0x7)
	else:
		return(z - 1,         8,
		       x >> 3 & 0x1F, y >> 3 & 0x1F,
			   x      & 0x7,  y      & 0x7)

# Convert world coordinates to chunk number, and return x,y offset into chunk.
def world_to_chunk_num(wx, wy, wz):
	scx, scy, cx, cy, tx, ty = world_to_chunk(wx, wy, wz)
	if wz == 0: cw = 16
	else:       cw = 32

	schunk = scx + scy * 8   # 8x8 superchunks / map
	chunk = map[schunk][cx + cy * cw]     # 16x16 chunks / schunk
	return chunk, tx, ty

# Unfortunately this is redundant with world_to_chunk_num, but I can't make that
# function an lvalue.
def set_chunk_at(chunk, wx, wy, wz):
	global map_dirty
	scx, scy, cx, cy, tx, ty = world_to_chunk(wx, wy, wz)
	if wz == 0: cw = 16
	else:       cw = 32

	schunk = scx + scy * 8   # 8x8 superchunks / map
	map[schunk][cx + cy * cw] = chunk    # 16x16 chunks / schunk
	map_dirty = 1

# Return and/or set the map tile number at the specified world coordinates.
# FIXME Set operation not permitted yet.
def maptile_at(wx, wy, wz):
	chunk, tx, ty = world_to_chunk_num(wx, wy, wz)
	return chunks[chunk][tx + ty * 8]     # 8x8 tiles / chunk

def set_maptile_at(t, wx, wy, wz):
	global chunks_dirty
	chunk, tx, ty = world_to_chunk_num(wx, wy, wz)
	chunks[chunk][tx + ty * 8] = t
	chunks_dirty = 1

if __name__ == '__main__':
	from os import chdir
	chdir('files')
	read()
	print(len(chunks))
	print(len(map))
	write()
