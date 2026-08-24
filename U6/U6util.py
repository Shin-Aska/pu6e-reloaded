
import re
from U6 import obj
from U6 import book, tile, look

# Walk objects using a generator.
def walk_objects(objs, depth=0):
	for obj in objs:
		yield depth, obj
		if obj.contains:
			for c in walk_objects(obj.contains, depth + 1):
				yield c

def output_objects(objs):
	if objs is None: return
	for depth, obj in walk_objects(objs):
		t = obj.tile
		name = look.get_obj_name(t)
		pre = "   " * depth
		article = tile.article(t)
		parsed_name = obj.name()

		if re.search(r'^book|scroll|picture$', name):
			b = obj.quality - 1
			if b >= 0:
				contents = book.books[b]
			else:
				contents = "(none)"
			print(pre + "      book contents: " + contents)

		print(pre + "   object:  %04x %s -> %s (%s stones)" % (t, name, parsed_name, obj.weight_total()/10.0))

# This is the same as output_objects, but without using the walk_objects generator.
def output_objects_traverse(depth, objs):
	for obj in objs:
		t = obj.tile
		name = look.get_obj_name(t)
		pre = "   " * depth
		article = tile.article(t)
		parsed_name = get_parsed_name(obj)

		if re.search(r'^book|scroll|picture$', name):
			b = obj.quality - 1
			if b >= 0:
				contents = book.books[b]
			else:
				contents = "(none)"
			print(pre + "      book contents: " + contents)

		print(pre + "   object:  %04x %s -> %s" % (t, name, parsed_name))
		if obj.contains:
			output_objects(depth + 1, obj.contains)

def get_tile_name(t):
	name = look.get_obj_name(t)
	if not name: return "nothing", "nothing"
	parsed_name = name
	article = tile.article(t)
	if article:
		parsed_name = article + " " + parsed_name
	return (name, parsed_name)

def get_parsed_name(obj):
	t = obj.tile
	name = look.get_obj_name(t)
	if not name: return "nothing"
	article = tile.article(t)
	qty = obj.qty()

	if qty == 0 or qty == 1:
		# Singular object.
		name = re.sub(r"\\[A-Za-z]*", "", name) # Remove plural modifier, e.g. \ves
		name = re.sub('/', '', name)            # Remove singular prefix /
		if qty == 1:
			article = repr(qty)
		if article:
			name = article + " " + name

	else:
		# Plural object.
		name = re.sub('/[A-Za-z]*', '', name)   # Remove singular modifier, e.g. /f
		name = re.sub(r'\\', '', name)          # Remove plural prefix \
		name = repr(qty) + " " + name

	return name

def object_description(o):
	parsed_name = o.name()
	msg = " * Thou dost see " + parsed_name + "."
	weight = o.weight_total()
	if weight != 0 and weight != 255:
		msg += " It weighs %s stones." % (weight / 10.0)
	return msg

from U6 import Map
# Return the object that you would see if performing a "Look" command at wx, wy.
# If None, you should check the maptile.
# Note: the lowest_look logic here won't work for double-size tiles, but that
# doesn't happen in U6 anyway.
# Note: NPCs are not currently considered frontmost, as in the game.
def lookable_at(wx, wy, wz):
	o = None
	objects = obj.objects_at(wx, wy, wz)
	if objects:
		o = objects[-1]   # topmost object
		if not tile.lowest_look(o.tile):   # save for later if "lowest" tile
			return o                       # otherwise, this is it

	# (Assumes coordinates wrap.)
	return lookable_adjacent(wx, wy, wz, 1, 0) or \
	       lookable_adjacent(wx, wy, wz, 0, 1) or \
	       lookable_adjacent(wx, wy, wz, 1, 1) or o

def lookable_adjacent(wx, wy, wz, dx, dy):
	for o, t in gen_adjacent(wx, wy, wz, dx, dy):
			return o
	return None

# Helper func for lookable_at: check adjacent tiles.
# Only 0 or 1 is a valid input to dx and dy; and both can't be zero.
def gen_adjacent(wx, wy, wz, dx, dy):
	dx &= 1; dy &= 1
	size = (dx << 1) | dy    # double width, height or both
	objects = obj.objects_at(wx+dx, wy+dy, wz)
	if not objects: return
	for i in range(len(objects)):
		o = objects[ -(i+1) ]   # Iterate in reverse
		t = o.tile
		s = tile.size(t)
		if s & size == size:
			# Adjust for object size and desired tile.
			if dx: t -= 1
			if dy: t -= 1
			if dx and dy: t -= 1
			yield o, t

def blocked_at(wx, wy, wz):
	map_block = 0
	if tile.is_blocked(Map.maptile_at(wx, wy, wz)):
		# We might not be blocked, if there's a force-passable object here.
		map_block = 1
	objects = obj.objects_at(wx, wy, wz)
	# Check for blocking objects, and force-passable objects.
	if objects:
		for o in objects:
			if tile.is_blocked(o.tile):
				return 1
			if tile.force_passable(o.tile):
				map_block = 0
	# If maptile is still blocked, don't
	# bother checking adjacent objects.
	if map_block: return 1

	# Note: U6 doesn't check adjacent tiles for blocking objects
	# if a force_passable tile was found, but we do.

	for o, t in gen_adjacent(wx, wy, wz, 1, 0):
		if tile.is_blocked(t):
				return 1
	for o, t in gen_adjacent(wx, wy, wz, 0, 1):
		if tile.is_blocked(t):
				return 1
	for o, t in gen_adjacent(wx, wy, wz, 1, 1):
		if tile.is_blocked(t):
				return 1

	return 0
