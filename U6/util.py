from struct import unpack

def short(x):
	return unpack("<H", x)[0]

def file_copy(filename, backup):
	f = open(filename, 'rb')
	b = open(backup, 'wb')
	b.write(f.read())
	f.close()
	b.close()

def file_backup(filename):
	backup = filename + ".bak"
	try:
		file_copy(filename, backup)
	except OSError as s:
		print("* Error backing up %s (%s)." % (filename, s))
		raise OSError(s)
