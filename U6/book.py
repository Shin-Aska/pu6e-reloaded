#!/usr/bin/env python

import re
import sys
from U6.util import short

default_fn = "book.dat"
books = []

def read(game='fp'):
	global books
	if not game == 'fp':
		books = [''] * 128
		return 0          # Don't understand MD/SE books; return empty set
	f = open(default_fn, "rb")
	parse(f.read())

def parse(buf):
	global books

	buf = buf[256:]
	r = re.compile(br"(.*?)\0", re.DOTALL)
	# packed will be a flat list of strings
	books = [value.decode("cp437") for value in r.findall(buf)]

def contents(book):
	if 0 <= book < len(books):
		return books[book]
	else:
		return "[This book has no contents.]"

def num_books():
	return len(books)

if __name__ == '__main__':
	from os import chdir
	chdir('files')
	read()
	# One invalid value will stop execution
	indices = list(map(int, sys.argv[1:]))
	if not indices:
		indices = range(len(books))
	for i in indices:
		print("---- %s: --" % i)
		try:
			print(books[i])
		except IndexError:
			print("error: book %s out of range 0 - %s" % (i, len(books)))
