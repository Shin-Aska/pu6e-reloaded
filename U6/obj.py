#!/usr/bin/env python

# FIXME Obj.type stores the frame + type encoded, and there's no function
# to extract it--we always do it manually.

import re
import sys
import os, os.path
from io import BytesIO
from struct import unpack, pack
from U6.util import short, file_copy
from U6 import Config
from array import array
# from Pseudohash import Pseudohash
from U6 import look, tile, Point
import copy

OBJ_REAGENT_START = 0x41
OBJ_REAGENT_END   = 0x48
OBJ_GOLD_COINS    = 0x58

default_fn = { 'objblk': "savegame/objblk",
               'basetile': "basetile"
}
objblk = []
# NPC data is stored in the objblks, so we read it here
# into a (temporary) array.
objnpc = [ [] for i in range(256) ]

# I'm not sure of the idiomatic python way for a list to spontaneously
# spring into existence upon append, so I add a contains list to all objects.
class Obj(object):  # was derived from 'object'
	fields = { 'x': 0, 'y': 1, 'status': 2, 'tile': 3 }

	def __init__(self, **kw):
		self.contains = []
		self.__dict__.update(kw)
		# This is merely a convenience for callers, and relies on basetile
		# being populated (as it should be).
		self.tile = map_type_to_tile(self.type)
		# Pseudohash.__init__(self, **kw)

	# Debugging: print object information
	# Assumes you've filled in the necessary attributes.
	def print_info(self, depth=0):
		pre = "\t" * depth
		# I saw a way to override the print function before that would
		# let us be rid of "pre +".
		# We don't store h, d1, or d2 packed coords any more: saves
		# about 4 megs! ;)
		h, d1, d2 = pack_coords(self.x, self.y, self.z)
		print(pre + "status: %02x x: %03x y: %03x z: %d " \
		      "h: %02x d1: %02x d2: %02x" % (self.status, self.x, self.y, self.z, h, d1, d2))
		print(pre + "type: %04x (%04x frm %d) quantity: %02x quality: %02x" % \
			  (self.type, self.type & 0x3ff, self.type >> 10, self.quantity, self.quality))
		print(pre + "name: " + look.get_obj_name(map_type_to_tile(self.type)));
		print()

	def print_info_recursive(self, depth=0):
		self.print_info(depth)
		for obj in self.contains:
			obj.print_info_recursive(depth + 1)

	def __repr__(self):
		return "<Obj %03x \"%s\" at (%03x, %03x, %d)>" % (self.type & 0x3ff, look.get_obj_name(self.tile), self.x, self.y, self.z)

	def clone(self):
		return copy.deepcopy(self)

	def in_container(self):
		# bit 3: contained (as long as bit 4, in_npc, is clear)
		return self.status & 0x18 == 0x08

	def in_inventory(self):
		# Note: includes readied items.
		return self.status & 0x10

	def is_readied(self):
		# Container bit is overloaded for readied items.
		return self.status & 0x18

	def is_npc(self):
		return 0

	def is_containable(self):
		# Objects can be contained.
		return 1

	def is_unknown(self):
		# We now handle all bits.
		return self.status & 0x00

	def weight_total(self):
		# Return weight of object * 10.
		w = 0
		for o in self.contains:
			w += o.weight_total()
		my_w = self.weight()
		q = self.qty()
		if q > 1:
			my_w *= q

		# Some objects have 1/10th weight [and decimals are lopped off
		# after the quantity multiplier].
		if OBJ_REAGENT_START <= self.type <= OBJ_REAGENT_END \
		   or self.type == OBJ_GOLD_COINS:
			my_w = int(my_w / 10)

		return w + my_w

	def weight(self):
		# Return 10 * weight of object.  Do not adjust for contained items or quantity.
		return tile.weight(self.type & 0x3ff)

	def qty(self):
		# Return object quantity.
		# Hack: treat as a quantity 0 (singular) object if the name
		# cannot be transformed into the plural.  Takes care of
		# quantity on chests, doors, etc., since I can't distinguish this otherwise.
		name = look.get_obj_name(self.tile)
		if not re.search(r"\\", name):
			return 0
		else:
			return self.quantity

	def frame(self):
		return self.type >> 10

	def set_frame(self, frame):
		t = map_frame_to_type(frame, self.type)
		self.set_type(t)

	def set_type(self, type):
		self.type = type
		self.tile = map_type_to_tile(type)

	def basetype(self):
		return self.type & 0x3ff

	def name(self):
		t = self.tile
		name = look.get_obj_name(t)
		if not name: return "nothing"
		article = tile.article(t)
		qty = self.qty()

		if qty == 0 or qty == 1:
			# Singular object.
			name = re.sub(r"\\[A-Za-z]*", "", name) # Remove plural modifier, e.g. \ves
			name = re.sub('/', '', name)			# Remove singular prefix /
			if qty == 1:
				article = repr(qty)
			if article:
				name = article + " " + name

		else:
			# Plural object.
			name = re.sub('/[A-Za-z]*', '', name)   # Remove singular modifier, e.g. /f
			name = re.sub(r'\\', '', name)		  # Remove plural prefix \
			name = repr(qty) + " " + name

		return name

	def num_frames(self):
		t = self.type & 0x3ff
		if t + 1 == len(basetile):
			next = len(tile.maptiles)
		else:
			next = basetile[t + 1]

		return next - basetile[t]

	# Insert object into container, massaging its attributes as needed.
	def insert(self, i, o):
		# I'm sure these checks slow us down.
		if not isinstance(o, Obj):
			raise TypeError("Attempted to insert non-object %s into %s" % (o, self))
		if not o.is_containable():
			raise TypeError("Attempted to insert non-containable object %s into %s" % (o, self))
		o.y = 0            # Set explicit y value for containers.
		o.status |= 0x08   # Set container status
		self.contains.insert(i, o)

	def __iter__(self):
		return iter(self.contains)

	def __delitem__(self, key):
		return self.contains.__delitem__(key)

def read(fn=default_fn):
	parse_basetile(open(fn['basetile'], 'rb'))
	parse_blocks(fn['objblk'])
	# Debugging: only read one file
	# parse_block(open(fn['objblk'] + 'cc', 'rb'))

# Parse all surface (a..h) blocks.
# This accepts a file name, not an open file object.
def parse_blocks(fn):
	global objblk
	objblk = []

	# (string.ascii_lowercase[0:8] will also yield 'abcdefgh'.)
	for j in 'abcdefgh':
		for i in 'abcdefgh':
			f = open(fn + i + j, "rb")
			block = parse_block(f)
			objblk.append(block)

	for i in 'abcde':
		f = open(fn + i + 'i', "rb")
		block = parse_block(f)
		objblk.append(block)

def unpack_coords(h, d1, d2):
	x = ((d1 & 0x03) << 8) | h
	y = ((d2 & 0x0F) << 6) | ((d1 & 0xFC) >> 2)
	# This may not all be z coordinate, but we do need to save it.
	z =  (d2 & 0xF0) >> 4
	return x, y, z

def pack_coords(x, y, z):
	h = x & 0xFF
	d1 = (x >> 8 & 0x03) | (y << 2 & 0xfc)
	d2 = (y >> 6 & 0x0F) | (z << 4 & 0xF0)
	return h, d1, d2

# Parse one block referenced by filehandle 'f'.
def parse_block(f):
	global changes
	changes = {}     # Zero out any previous changes.
	block = []
	objidx = []
	num_objs = unpack("<H", f.read(2))[0]
	cur_x, cur_y = -1, -1
	row, point = [], []

	for i in range(num_objs):
		status, h, d1, d2, type, quantity, quality = unpack("<BBBBHBB", f.read(8))
		x, y, z = unpack_coords(h, d1, d2)
		obj = Obj( status=status, x=x, y=y, z=z,
		           type=type, quantity=quantity, quality=quality )

		if obj.in_container():
			# x-coordinate stores index of container.  This is a bit more
			# lenient than the game code.  Note: the lower bits of the
			# y-coord are shifted onto the top of the index, so that
			# we can access items above 1024 (but not sure how many bits
			# are significant--we'll say lower two).
			idx = x | ((y & 0x3) << 10)
			container = objidx[idx]
			container.contains.append(obj)
		elif obj.in_inventory():
			# x-coord stores NPC number (0-255).
			objnpc[x].append(obj)
		else:
			if y != cur_y:
				row.reverse()       # reverse previous row, since we're done
				row = []            # Y changed; create a new row
				block.append([y, row])
			if x != cur_x or y != cur_y:
				point.reverse()     # reverse previous point, since we're done
				point = Point.Point(x, y, z)      # X or Y changed; create a new (x, y) container
				row.append([x, point])
			point.append(obj)
			cur_x, cur_y = x, y
		# Push (refs to) all objects onto the index array, so
		# we can refer back to containers correctly.
		objidx.append(obj)

	# Reverse objects so they appear in drawing order.  This appears to
	# exhibit no performance penalty.  Note: We reverse the row and point containers
	# above as well, as they are built.  However, we have to manually reverse the
	# last instance of each, since the reverse is only triggered above when a new
	# row or point is detected.
	point.reverse()
	row.reverse()
	block.reverse()
	return block

def write_changes(fn=default_fn):
	changed = list(changes.keys())
	if not changed:
		print("  No objblk changes to save.")

	for block in changed:
		id = block_num_to_id(block)
		# FIXME: we should write into a tmp file, then move it into place.
		# (But note renaming over an existing file may not work in Windows.)
		filename = os.path.join(Config.gamedir, fn['objblk'] + id)
		backup = filename + ".bak"
		print("- writing block %s (%d)" % (id, block))

		try:
			file_copy(filename, backup)
		except OSError as s:
			print("* Error backing up %s (%s).  Aborting write." % (filename, s))
			return 0

		f = open(filename, 'wb')
		write_block(block, f)
		f.close()
		del changes[block]
	return 1

def clear_changes():
	global changes
	changes = {}

def write_block(block, f):
	f.seek(2)

	block = objblk[block][:]
	block.reverse()

	index = 0

	for y, row in block:
		row = row[:]
		row.reverse()
		for x, point in row:
			point = point[:]
			point.reverse()
			index = write_objects(point, None, f, index)

	f.seek(0)
	num_objs = pack("<H", index)
	f.write(num_objs)


def write_objects(objs, parent, f, index):
	from U6.NPCs import NPC    # blargh
	container_index = index - 1   # Index of parent (container) object.
	for o in objs:
		if not isinstance(o, Obj):
			raise ValueError("object %s in parent %s is a %s, not an Object" % (o, parent, o.__class__))

		if o.is_npc():
			# print "write: not writing NPC as object", o
			pass
		else:
			y, z = o.y, o.z
			status = o.status

			if isinstance(parent, Obj):
				if parent.is_npc():
					# This is an object in inventory.  Objects in containers held
					# by NPCs are not considered to be in inventory for this purpose.
					if not status & 0x10:
						# If the NPC inventory bit is not set, set it, and clear
						# the readied bit since we can't trust it and we might
						# lose items that way.
						status |= 0x10
						status &= ~0x08
					x = parent.id   # Not sure about y and z.
				else:
					# Object in a regular container.
					status = (status & ~0x10) | 0x08
					x = container_index & 0x3ff
					# The upper bits of y are still mysterious, so I'm leaving them alone.
					y = (y & ~0x3) | (container_index >> 10 & 0x03)
			else:
				# Top-level object.  Parent should be a Point, but we don't check for it.
				status &= ~0x18
				# FIXME We trust the object's coordinates, but to be safer
				# we could get them from the containing Point.
				x = o.x

			h, d1, d2 = pack_coords(x, y, z)
			str = pack("<BBBBHBB", status, h, d1, d2, o.type, o.quantity, o.quality)

			f.write(str)
			index += 1

		# Both NPCs and objects should have their insides written out.
		if o.contains:
			# print o, "contains", o.contains, "at index", index
			index = write_objects(o.contains, o, f, index)

	return index

def parse_basetile(f):
	global basetile
	buf = f.read()
	# Note: unpack returns an (immutable) tuple.  Use list() if editing desired.
	basetile = unpack("<%dH" % (len(buf)/2), buf)

# Return desired frame of object.  Note that this will cause overhead when looking up the name
# of an object with several frames (since that requires the last frame).
def map_type_to_tile(type):
	return basetile[(type & 0x3ff)] + (type >> 10)

def map_frame_to_type(frame, type):
	return (type & 0x3ff) | (frame << 10)

# Convert world coordinates to object block number.
# World coordinates are wrapped for you.
def world_to_block(wx, wy, wz):
	if wz == 0:
		return ((wx & 1023) >> 7) + ((wy & 1023) >> 7) * 8
	else:
		return (63 + (wz & 7))   # FIXME This isn't a perfect wrap.

# Return (wx, wy, wz) coordinates of upper left tile of object block.
def block_to_world(block):
	if block < 64:
		# 8x8 surface superchunks, 128x128 tiles each.
		return ((block & 7) * 128, (block >> 3) * 128, 0)
	else:
		return (0, 0, block - 63)

def block_num_to_id(block):
	a = ord('a')
	if block < 64:
		x = block % 8
		y = block // 8
		return chr(a+x) + chr(a+y)
	else:
		return chr(a+block-64) + 'i'

def objects_at(wx, wy, wz):
	block_num = world_to_block(wx, wy, wz)
	block = objblk[block_num]

	# Objects are stored right-to-left, then bottom-to-top.
	for y, row in block:
		if y < wy: break
		if y > wy: continue

		for x, point in row:
			if x < wx: break
			if x == wx:
				return point   # note: this is not a copy

	return None

# Mark block corresponding to coordinates as dirty.
def updated_at(wx, wy, wz):
	block_num = world_to_block(wx, wy, wz)
	changes[block_num] = 1

# Add object at specified coordinates.  x, y, and z coordinates of
# the object are updated by Point.
def add_object_at(obj, wx, wy, wz):
	point = add_point_at(wx, wy, wz)
	point.append(obj)
	updated_at(wx, wy, wz)

def add_point_at(wx, wy, wz):
	block_num = world_to_block(wx, wy, wz)
	block = objblk[block_num]

	# Create a new Point, in case
	# an equivalent Point does not exist.
	p = Point.Point(wx, wy, wz)

	# Is there a C func that finds first elt that satisfies a constraint?
	i = 0
	for i in range(len(block)):
		y, row = block[i]
		if y < wy:    # We went too far; create a new row with this object
			block.insert(i,  [wy, [[wx, p]]])
			return p
		elif y == wy:
			for j in range(len(row)):
				x, point = row[j]
				if x < wx:   # Went too far; create a new point with only this object
					row.insert(j, [wx, p])
					return p
				elif x == wx:
					# Return existing point.
					return point

			# Corner case: no matching or greater x found (we're at the end).
			# print "corner x: index %d wx, wy %03x, %03x obj %s" % (i, wx, wy, obj)
			row.append([wx, p])
			return p

	# Corner case: no matching or greater y found (we're at the end).
	# print "corner y: index %d wx, wy %03x, %03x obj %s" % (i, wx, wy, obj)
	block.append([wy, [[wx, p]]])
	return p

# Remove object at specified coordinates.  obj must be an actual reference to
# the object to remove.
# FIXME The point should be removed from the enclosing objblk structure
# if it is empty.
def remove_object_at(obj, wx, wy, wz):
	objs = objects_at(wx, wy, wz)
	if not objs: return 0

	for i in range(len(objs)):
		if objs[i] is obj:
			del objs[i]
			block = world_to_block(wx, wy, wz)
			changes[block] = 1    # Set this block to dirty.
			return 1
	return 0

# A default object (currently a leather helm)
def default_object():
	return Obj(x=0,y=0,z=0,status=0,type=1,quantity=0,quality=0)

# Helper funcs for debugging
def display_objblk(which):
	# By default, display all blocks.
	if not which:
		which = list(range(len(objblk)))
	for b in which:
		print("*** block %d\n" % (b, ))
		for y, row in objblk[b]:
			for x, col in row:
				for obj in col:
					obj.print_info_recursive()
		# for obj in objblk[b]:
		# 	obj.print_info_recursive()

def display_npc_inv(which):
	if not which:
		which = list(range(len(objnpc)))
	for i in which:
		print("*** npc %d\n" % i)
		for obj in objnpc[i]:
			obj.print_info_recursive()

# Main

if __name__ == '__main__':
	from os import chdir
	from getopt import getopt, GetoptError
	from U6 import Config

	def usage():
		print("""\
usage: %s    blk1, blk2, blk3, ...
       %s -n npc1, npc2, npc3, ...
Display contents of objblk or npc inventory.  Default is to show all items.""" \
                                                  % (sys.argv[0], sys.argv[0]))
		sys.exit()

	Config.read('pu6e.conf')
	chdir(Config.gamedir)
	# chdir('files')
	print(Config.gametype)
	look.read(Config.gametype)
	read()

	try:
		optlist, which = getopt(sys.argv[1:], 'n')
	except GetoptError as s:
		usage()

	which = [ int(b) for b in which ] # Change to int(b,0) to parse hex;
	                                  # but won't work with ints then.
	for o, a in optlist:
		if o == '-n':
			display_npc_inv(which)
			sys.exit()

	display_objblk(which)
