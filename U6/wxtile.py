from wx import *
from . import tile
import fastgl
from array import array

palette = None
bitmap  = None
initialized = 0

def indexed_to_rgb(data):
	rgb = []
	for i in data:
		rgb.extend(palette.pal[i])
	return array('B', rgb).tobytes()

indexed_to_rgb = fastgl.indexed_to_rgb   # Use the C version of this code

def maptile_to_bitmap(num):
	data = indexed_to_rgb(tile.maptiles[num], palette)
	image = Image(16, 16)
	image.SetData(data)
	return Bitmap(image)

# The wx subsystem must be initialized before
# calling this function.  Until I figure out how to
# do it otherwise, each window must call this function
# separately (though it will only have an effect the first time)
def init(pal):
	global palette, bitmap, initialized
	if initialized: return bitmap

	palette = pal.tobytes()  # redundant with render
	print("Converting tiles to bitmaps...")
	bitmap = [ maptile_to_bitmap(i) for i in range(len(tile.maptiles)) ]
	initialized = 1
	return bitmap
