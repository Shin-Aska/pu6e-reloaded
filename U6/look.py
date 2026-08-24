#!/usr/bin/env python

import re
from U6.util import short
from U6 import lzw
from struct import unpack
from U6 import Config

read_file = Config.read_file   # alias

look = {}

def read(game='fp'):
	parse(read_file('look', game))

def parse(buf):
	global look
	r = re.compile(br"(..)(.*?)\0", re.DOTALL)
	# packed will be a list of tuples: (packed short, string)
	packed = r.findall(buf)

	# Create a dict mapping tile number to description
	look = {}
	for i in packed:
		look[short(i[0])] = i[1].decode("cp437")

# Search for object name, given a tile number.  Look data that is identical
# for a series of tiles is linked to the last tile number of the series.
# Note: there's an object (sentinel?) at 0x800.
def get_obj_name(tile):
	for i in range(tile, 0x800 + 1):
		if i in look:
			return look[i]
	return None


if __name__ == '__main__':
	from os import chdir
	chdir('/home/jim/dl/u6/ultima_se/')
	#chdir('files')
	read('se')
	print(look)
	print("object 2:", get_obj_name(2))
