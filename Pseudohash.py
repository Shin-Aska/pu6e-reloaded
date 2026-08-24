class Pseudohash(list):
	fields = {}

	def __init__(self, **kw):
#		print "self.fields = " + `self.fields`
		self[:] = [0] * len(self.fields)
		for k,v in list(kw.items()):
#			print "adding key %s with value %s" % (k, v)
			setattr(self, k, v)

	def __setattr__(self, key, val):
		if key in self.fields:
#			print "setattr field: key %s val %s" % (key, val)
			self[self.fields[key]] = val
		else:
#			print "setattr      : key %s val %s" % (key, val)
			self.__dict__[key] = val

	def __getattr__(self, key):
		if key in self.fields:
			return self[self.fields[key]]
		else:
			raise AttributeError(key)

if __name__ == '__main__':
	x = Obj(g=3, y=2)
	x.a = 2
	x.a
	print(x.x)
	x.x = 3
	print(x.x)
	print(x.y)
	x.y = 2
	print(x)
