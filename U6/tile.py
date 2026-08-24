#!/usr/bin/env python

import re
import sys
from io import BytesIO
from struct import unpack
from U6.util import short
from array import array
from U6 import lzw
import numpy as Numeric
from U6 import Config

# Hardcoded hybrid source and dest tile data from u6mcga.drv.
# Each value needs to be halved (later) since they're pointers to
# the tiles in tileindx.vga, each of which is a word.
hybrid_src = [ 0x16,0x16,0x1a,0x1a,0x1e,0x1e,0x12,0x12,
               0x1a,0x1e,0x16,0x12,0x16,0x1a,0x1e,0x12,
               0x1a,0x1e,0x1e,0x12,0x12,0x16,0x16,0x1a,
               0x12,0x16,0x1e,0x1a,0x1a,0x1e,0x12,0x16 ]
hybrid_dest = list(range(32, 32+64, 2))

hybrids = []
tileflag = []
masktypes = []
anim = {}
maptiles = []

read_file = Config.read_file   # alias

def read():
	parse_tileflag(read_file('tileflag'))
	parse_masktypes(read_file('masktypes'))
	parse_tileindx(read_file('tileindx'))
	parse_animdata(read_file('animdata'))
	b = read_file('maptiles') + read_file('objtiles')
	parse_maptiles(b)
	parse_animmask(read_file('animmask'))

def parse_tileflag(buf):
	global tileflag
	# unpack is about 2.5x faster.
	# Perl is about 1.1x faster still.
	# tileflag = [ ord(i) for i in buf ]
	tileflag = unpack("%dB" % len(buf), buf)

def parse_masktypes(buf):
	global masktypes
	# There are extra unknown bytes in the masktypes file.
	buf = buf[0:0x800]
	masktypes = unpack("%dB" % len(buf), buf)

def parse_tileindx(buf):
	global tileindx
	tileindx = unpack("<%dH" % (len(buf) // 2), buf)

def parse_animdata(buf):
	global anim
	# Unfortunately, unpack returns a flat list,
	# so I have to read one variable at a time.
	sio = BytesIO(buf)
	anim['numtiles']     = unpack("<H",   sio.read( 2))[0];
	anim['tiles']        = unpack("<32H", sio.read(64));
	anim['first_frame']  = unpack("<32H", sio.read(64));
	anim['and_masks']    = unpack("<32B", sio.read(32));
	anim['shift_values'] = unpack("<32B", sio.read(32));

# Parse animmask data and populate hybrids list with tuple
# (dest tile, src tile, mask).  Mask will contain one value
# for each pixel, 1 to copy, 0 to skip.
# Format: 32 * block
#         block = 32 * (bytes_to_copy, displacement)
#         bytes_to_copy = byte
#         displacement  = byte, 0 to terminate
def parse_animmask(buf):
	global hybrids
	hybrids = []
	if not buf: return 0    # Hybrids disabled (assume MD/SE).

	sio = BytesIO(buf)
	i = 0

	while 1:
		control = sio.read(64)
		if not control: break
		mask = animmask_to_mask(control)
		h = (hybrid_dest[i] // 2, hybrid_src[i] // 2, mask)  # note: halve src & dest
		hybrids.append(h)
		i += 1

	if i != len(hybrid_src) or i != len(hybrid_dest):
		raise ValueError("hybrid src, dest and masks are not all the same length")

def animmask_to_mask(buf):
	mask = Numeric.zeros(256 * 4)  # FIXME Temporarily using RGBA
	sio = BytesIO(buf)
	index = 0
	while 1:
		copy, disp = unpack("BB", sio.read(2))
		copy *= 4; disp *= 4       # FIXME Temporarily using RGBA
		mask[index:index+copy] = [1] * copy
		if disp == 0: break
		index += copy + disp

	return mask


def parse_maptiles(buf):
	global maptiles
	maptiles = []
	sio = BytesIO(buf)

	for i in range(len(masktypes)):
		if masktypes[i] == 0x0A:
			tiledata = bytearray(b"\xff" * 256)
			length = unpack("B", sio.read(1))[0]
#			print "tile %s len %s mt %s" % (i, length, len(masktypes))
			length = length * 16 - 1    # Value is in paragraphs.
			twisted = sio.read(length) # removeme
			twisted_io = BytesIO(twisted)
			tileidx = 0
			# We break on encountering a runlength of 0 [since the tile
			# can be padded with 0xED bytes], but also explicitly
			# stop at the end of the buffer as well.
			while twisted_io.tell() < length:
				# Convert one run of pixels
				add, runlength = unpack("<HB", twisted_io.read(3))
				if runlength == 0: break
				run = twisted_io.read(runlength)

				actual_add = add % 160
				if add >= 1760:
					actual_add += 160
				tileidx += actual_add
				tiledata[tileidx:tileidx + runlength] = run
				tileidx += runlength

			tiledata = bytes(tiledata)

		else:
			tiledata = sio.read(256)
		maptiles.append(tiledata)

def article(tile):
	art = (tileflag[0x1400 + tile] >> 6) & 0x3
	return ("", "a", "an", "the")[art]

# Return a 2-bit value representing tile size.
# If bit 1 set, object width is 2.
# If bit 0 set, object height is 2.
def size(tile):
	return (tileflag[0x800 + tile] >> 6) & 0x3

# Return 8-bit value representing the object weight * 10.
# Tile here represents object number (type), 0-0x3ff.
def weight(tile):
	return tileflag[0x1000 + tile]

# Return the height flag (0 = normal, 1 = above)
def height(tile):
	return (tileflag[0x800 + tile] >> 4) & 0x1

# This tile is considered last for look/use purposes (boolean).
def lowest_look(tile):
	return (tileflag[0x1400 + tile] & 0x10)

def is_blocked(tile):
	return (tileflag[tile] & 0x02)

# Maptile at same location is forced passable by this (object) tile.
def force_passable(tile):
	return (tileflag[0x1400 + tile] & 0x04)

if __name__ == '__main__':
	from os import chdir
	Config.read('pu6e.conf')
	chdir(Config.gamedir)
	read()
	print(list(map(article, list(range(512,550)))))
	print(anim)

#	for i in xrange(2000): read()

# No advantage
#	buf = open(default_fn['tileflag'], "rb").read()
#	for i in xrange(2000):
#		tileflag = unpack("7168B", buf)
