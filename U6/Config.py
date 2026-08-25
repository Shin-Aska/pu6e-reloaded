#!/usr/bin/env python

from configparser import ConfigParser
from struct import unpack
from U6 import dospath, lzw

screen_width  = None
screen_height = None
scale_factor  = None
gamedir       = None
gametype      = None

defaults = { 'width': 640,
             'height': 480,
			 'zoom': 1.0,
			 'gamedir': 'files',
			 'gametype': 'fp' }

##### File pathnames and metadata #####
LZW = 0x01     # File is LZW-compressed
LIBHDR = 0x02  # File has MD/SE style 'library' header
EMPTY = 0x04   # Return empty buffer for this file (i.e. unimplemented/not present)

false_prophet  = { 'look':      [ "look.lzd",     LZW ],
                   'tileflag':  [ "tileflag",     0],
			       'tileindx':  [ "tileindx.vga", 0],
			       'animdata':  [ "animdata",     0],
			       'masktypes': [ "masktype.vga", LZW],
			       'maptiles':  [ "maptiles.vga", LZW],
			       'objtiles':  [ "objtiles.vga", 0],
			       'animmask':  [ "animmask.vga", LZW]
}

martian_dreams = { 'look':      [ "look.lzc",     LIBHDR],
                   'tileflag':  [ "tileflag",     0],
			       'tileindx':  [ "tileindx.vga", 0],
			       'animdata':  [ "animdata",     0],
			       'masktypes': [ "masktype.vga", LIBHDR],
			       'maptiles':  [ "maptiles.vga", LIBHDR],
			       'objtiles':  [ "objtiles.vga", 0],
			       'animmask':  [ "animmask.vga", EMPTY]
}

savage_empire  = martian_dreams

paths = { 'fp': false_prophet, 'md': martian_dreams, 'se': savage_empire }
######

def read(f):
	global screen_width, screen_height, scale_factor, gamedir, gametype

	c = ConfigParser()
	c.read(f)
	s = 'pu6e'

	screen_width  = c.getint(s, 'width')
	screen_height = c.getint(s, 'height')
	scale_factor  = c.getfloat(s, 'zoom')
	gamedir       = c.get(s, 'gamedir')
	gametype      = c.get(s, 'gametype')

# 'name' is actually a key into the paths dict.
# This should probably be a utility function.
def read_file(name, game=None):
	if game == None: game = gametype
	fn, enc = paths[game][name]
	if enc & EMPTY:
		return b""   # Return empty buffer for this file.

	f = open(dospath.resolve_dos_path(fn), "rb")
	b = f.read()
	f.close()
	if enc & LZW:
		b = lzw.decompress_buffer(b)
	if enc & LIBHDR:
		buflen, start = unpack("<IH", b[0:6])
		if len(b) != buflen:
			raise ValueError("%s: File size %d does not match \
			                       size %d in library header" % (fn, len(b), buflen))
		b = b[start:]   # skip start bytes; rest of header data unknown
	return b

if __name__ == '__main__':
	read('pu6e.conf')
	print(screen_width, screen_height, scale_factor, gamedir)
