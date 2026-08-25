#!/usr/bin/env python

from io import BytesIO
from struct import unpack, pack
import numpy as Numeric
import os
from . import obj
from U6 import Config, dospath, look
from U6.util import file_backup

default_fn = { 'objlist':   "savegame/objlist",
}

npcs = Numeric.zeros(256, object)

class NPC(obj.Obj):
	fields = { 'x': 0, 'y': 1, 'status': 2, 'tile': 3 }

	def __init__(self, **kw):
		self.__dict__.update(kw)
		self.quality = 0
		self.quantity = 0
		self.contains = obj.objnpc[self.id]  # warning: you must set .id
		self.status = 0   # Not used for NPCs, but some functions that handle Objects expect it.

	def __str__(self):
		return "<NPC %d at (%03x, %03x, %d)>" % (self.id, self.x, self.y, self.z)

	def frame(self):
		return self._frame   # We should probably just return self.type >> 10 like obj

	def set_frame(self, frame):
		self._frame = frame   # Should probably do bounds check.
		self.type = obj.map_frame_to_type(frame, self.type)
		self.tile = obj.map_type_to_tile(self.type)

	# Consider total NPC weight to be 0 for now (improves parsed display, though
	# ObjEdit will also show 0).
	def weight_total(self):
		return 0

	def is_npc(self):
		return 1

	def is_containable(self):
		return 0   # Can't put NPCs in a container.

	def clone(self):
		return None   # Can't clone NPCs

	def insert(self, i, o):
		obj.Obj.insert(self, i, o)
		o.status |= 0x10   # Turn on NPC inventory bit.
		o.status &= ~0x08  # Turn off readied bit, for safety.

def read(fn=default_fn):
	f = open(dospath.resolve_dos_path(fn['objlist']), "rb")
	parse_npcs(f.read())

def parse_npcs(buf):
	sio = BytesIO(buf)
	sio.seek(0x100)

	for i in range(256):
		b1, b2, b3 = unpack("BBB", sio.read(3))
		x, y, z = obj.unpack_coords(b1, b2, b3)
		npc = NPC(x=x, y=y, z=z, id=i)
		npcs[i] = npc

	for i in range(256):
		b1, b2 = unpack("BB", sio.read(2))
		t = b1 | ((b2 & 0x03) << 8)
		f =       (b2 & 0xfc) >> 2
		# npcs[i].basetype  = t   # FIXME necessary?
		npcs[i]._frame    = f   # This is a bit roundabout
		npcs[i].type     = obj.map_frame_to_type(f, t)
		npcs[i].tile     = obj.map_type_to_tile(npcs[i].type)

def write(fn=default_fn):
	filename = os.fspath(dospath.resolve_dos_path(os.path.join(Config.gamedir, fn['objlist'])))
	file_backup(filename)
	f = open(filename, 'rb+')   # Don't destroy current contents.
	f.seek(0x100)
	for i in range(256):
		n = npcs[i]
		b1, b2, b3 = obj.pack_coords(n.x, n.y, n.z)
		str = pack("BBB", b1, b2, b3)
		f.write(str)

	for i in range(256):
		str = pack("<H", npcs[i].type)   # self.type includes frame number
		f.write(str)

	f.close()

# Add all NPCs as objects to the world.  Side-effect: clears the
# system's knowledge of any changes to objblks that have occurred.
def populate():
	for i in range(len(npcs)):
		n = npcs[i]
		if n.type == 0: continue
		if n.z > 5:
			print("skipping illegal z value", n)
			continue
		obj.add_object_at(n, n.x, n.y, n.z)
	obj.clear_changes()

if __name__ == '__main__':
	from U6 import Config
	from os import chdir
	conf = Config
	conf.read('pu6e.conf')
	chdir(conf.gamedir)
	obj.read()
	read()
	print(npcs)
