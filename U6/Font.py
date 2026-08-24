#!/usr/bin/env python

from io import BytesIO
from struct import unpack
import numpy as Numeric

default_fn = { 'font':   "u6.ch",
}

chardata = None    # Bitmap: 256 chars, 8 bytes/char, 8 bits / row
# Hardcoded pixel values from u6mgca.drv
on  = 0x48
off = 0x31
transparent = 0
# colors = [ off, on ]

def read(game='fp'):
	global chardata
#	if game != 'fp':
#		chardata = None
#		return 0
	fn = default_fn
	try:
		f = open(fn['font'], "rb")
		parse_font(f.read())
	except IOError:
		print("* Font unavailable.")
		chardata = None
		return 0
	return 1

def parse_font(buf):
	global chardata
	chardata = Numeric.frombuffer(buf, Numeric.uint8)
	chardata = Numeric.reshape(chardata, (256, 8))

# Return an 8-bit paletted representation of char 0-255.
# Transparency optional.
def convert_1_to_8(char, transp=0):
	if transp:
		colors = [ transparent, on ]
	else:
		colors = [ off, on ]

	c = chardata[char]
	p = Numeric.zeros(8 * len(c), Numeric.uint8)
	b = 0
	for i in c:
		for r in range(8):
			p[b] = colors[(i & 0x80) >> 7]    # top bit is first byte
			i <<= 1
			b += 1

	return p

if __name__ == '__main__':
	from U6 import Config
	from os import chdir
	conf = Config
	conf.read('pu6e.conf')
	chdir(conf.gamedir)
	read()
	print(chardata)
#	print "colors:", colors
	print(convert_1_to_8(ord('A')))
