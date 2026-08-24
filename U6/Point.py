# Collection of objects at the same point in space.  Behaves like a
# list, but coordinates and status of added objects are modified.
# Keeps track of its own location.  You should not modify the coordinates
# after initialization.
class Point(list):
	def __init__(self, x, y, z):
		self.coords = x, y, z
		list.__init__(self, [])

	def __setitem__(self, k, v):
		self._massage(item)
		list.__setitem__(self, k, v)

	def append(self, item):
		self._massage(item)
		list.append(self, item)

	def insert(self, i, item):
		self._massage(item)
		list.insert(self, i, item)

	def _massage(self, o):
		o.x, o.y, o.z = self.coords
		o.status &= ~0x18

	def __repr__(self):
		return "<Point (%03x, %03x, %d) %s>" % (self.coords + (self[:],))

if __name__ == '__main__':
	class Empty:
		def __init__(self, **kwargs):
			self.__dict__.update(kwargs)

	e = Empty(x=0, y=0, z=0, status=0xFF)
	p = Point(3, 4, 5)
	p.append(e)
	print(p)
	print(p[0].x, p[0].y, p[0].z, p[0].status)
