#!/usr/bin/env python

from struct import unpack
from array import array
from U6 import dospath

paths = { 'fp': "u6pal", 'md': 'mdpal', 'se': 'sepal' }

class pal:
	def __init__(self):
		self.pal = []

	def read(self, game='fp'):
		fn = paths[game]
		f = open(dospath.resolve_dos_path(fn), 'rb')
		self.parse(f)
		f.close()

	def parse(self, f):
		"""
		Parse an Ultima 6 format palette file.

		The main U6 palette file consists of 256 VGA RGB triples.
		Since the VGA DAC is only 6 bits, each value must
		be shifted left by 2.
		"""
		self.pal = []
		for i in range(256):
			triple = [ val << 2 for val in unpack("3B", f.read(3))]
			self.pal.append(tuple(triple))
		# Fudge a black transparent background color
		self.pal[-1] = (0, 0, 0)

	def rotate(self, len, *entries):
		p = self.pal
		len -= 1
		for i in entries:
			p.insert(i, p.pop(i + len))

	def tobytes(self):
		palarray = array('B')
		for tup in self.pal:
			palarray.fromlist(list(tup))
		return palarray.tobytes()

if __name__ == '__main__':
	from os import chdir
	chdir('/home/jim/dl/u6/ultima_se/')
	p = pal()
	p.read('se')
	print(p.pal)
