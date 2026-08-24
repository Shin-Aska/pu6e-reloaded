#!/usr/bin/env python

from wx import *
from U6 import tile, wxtile

TILE_WIDTH = 16
TILE_HEIGHT = 16
TILES_X = 16

class TileFrame(Frame):
	def __init__(self, parent, ID, title, pal, name_func=None):
		Frame.__init__(self, parent, ID, title,
			DefaultPosition,
			style=DEFAULT_FRAME_STYLE|FRAME_FLOAT_ON_PARENT) # | NO_FULL_REPAINT_ON_RESIZE)
		self.panel = TilePanel(self, NewIdRef(), pal, name_func)
		self.vbox = BoxSizer(VERTICAL)
		self.vbox.Add(self.panel, 1, EXPAND)
		self.SetSizer(self.vbox)
		self.Fit()

class TilePanel(Panel):
	def __init__(self, parent, id, pal, name_func=None):
		Panel.__init__(self, parent, id, style=TAB_TRAVERSAL|WANTS_CHARS)
		self.win = TileWindow(self, -1, pal)
		self.win.set_callback(self.updated)
		self.get_name = name_func
		self.label = StaticText(self, -1, "")
		self.vbox = BoxSizer(VERTICAL)
		self.vbox.Add(self.label, 0, EXPAND|ALL, 5)
		self.vbox.Add(self.win, 1, EXPAND)
		self.SetSizer(self.vbox)
		self.Fit()
		self.win.select_tile(0)
		self.win.SetFocus()

	def updated(self, tile):
		if self.get_name:
			name = self.get_name(tile)
		else:
			name = "(Name not available)"
		self.label.SetLabel("%d: %s" % (tile, name))

class TileWindow(ScrolledWindow):
	def __init__(self, parent, ID, pal):
		ScrolledWindow.__init__(self, parent, ID, style=SUNKEN_BORDER) #, size=Size(16*16, 16*8))

		self.tile_y = 0
		self.selected = None
		self.palette = pal
		self.bitmap = wxtile.init(self.palette)
		self.callback = None    # Updated callback.

		bgcolor = Colour(160, 160, 160)
		self.bgpen = Pen(bgcolor)
		self.SetBackgroundColour(bgcolor)

		self.SetScrollbars(TILE_WIDTH + 1, TILE_HEIGHT + 1,
		                   TILES_X, len(tile.maptiles) // TILES_X)

		EVT_PAINT(self, self.OnPaint)
		# Overriding OnErase fixes the flicker when we paint (select a tile, for
		# example) but not when we scroll.  However, MSW will not repaint the
		# background color automatically if OnErase is overridden.
		# EVT_ERASE_BACKGROUND(self, self.OnErase)
		EVT_LEFT_DOWN(self, self.MouseLeftDown)
		EVT_KEY_DOWN(self, self.OnKeyDown)

		# Set the size here instead of in the Scrolled constructor
		# so we take the scrollbars into account.
		w, h = TILES_X * (TILE_WIDTH + 1) + 1, 16 * (TILE_HEIGHT + 1) + 1
		self.SetClientSizeWH(w, h)
		# Hack: set the size twice because we ensure the
		# horizontal scrollbar has disappeared after the first time.
		self.SetClientSizeWH(w, h)

	def OnPaint(self, evt):
		dc = PaintDC(self)
		# Set scrolled origin correctly.  If we don't do this,
		# we have to calculate our own scrolling.
		self.PrepareDC(dc)
		# We should use GetViewStart / GetClientSize to
		# redraw the visible portion of the window.
		i = 0
		xpos = 1
		ypos = 1
		for y in range(0, 2048, 16):
			for x in range(0, 16):
				dc.DrawBitmap(self.bitmap[i], xpos, ypos)
				i += 1
				xpos += 17
			xpos = 1
			ypos += 17
		# Draw the selected rectangle, if present
		self.draw_selection(self.selected, dc, WHITE_PEN)

	def OnErase(self, evt):
#		print "erase"
		pass

	def OnKeyDown(self, evt):
		key = evt.GetKeyCode()
		if key == ord('T') or key == 27:
			self.GetParent().GetParent().Hide()
		else:
			evt.Skip()

	def draw_selection(self, t, dc, pen):
		if t != None:
			tx = t % TILES_X
			ty = int(t / TILES_X)
			ty -= self.tile_y
			x, y = tx * (TILE_WIDTH + 1), ty * (TILE_HEIGHT + 1)
			# dc.SetLogicalFunction(XOR)
			dc.SetPen(pen)
			dc.SetBrush(TRANSPARENT_BRUSH)
			dc.DrawRectangle(x, y, 18, 18)

	def MouseLeftDown(self, evt):
		x, y = self.CalcUnscrolledPosition(evt.m_x, evt.m_y)
		tx, ty = int(x / (TILE_WIDTH + 1)), int(y / (TILE_HEIGHT + 1))
		ty += self.tile_y
		tile = ty * TILES_X + tx
		self.select_tile(tile)

	def select_tile(self, t):
		dc = ClientDC(self)
		self.PrepareDC(dc)
		self.draw_selection(self.selected, dc, self.bgpen)
		self.selected = t
		self.draw_selection(self.selected, dc, WHITE_PEN)
		if self.callback:
			self.callback(self.selected)

	def set_callback(self, func):
		self.callback = func

class TileEditor(object):
	def __init__(self, parent, palette, name_func):
		self.frame = None
		self.parent = parent
		self.pal = palette
		self.name_func = name_func

	def create(self):
		self.frame = TileFrame(self.parent, -1, "Tile Viewer", self.pal, self.name_func)

	def Show(self, boolean=1):
		if not self.frame:
			self.create()
		self.frame.Show(boolean)

	def IsShown(self):
		if self.frame:
			return self.frame.IsShown()
		return 0

	def select_tile(self, t):
		if self.frame:
			self.frame.panel.win.select_tile(t)

	def selected(self):
		if self.frame:
			return self.frame.panel.win.selected
		else:
			return None

class TileEditApp(App):
	def OnInit(self):
		frame = TileFrame(None, NewIdRef(), "Tile Editor", palette)
		frame.Show()
		self.SetTopWindow(frame)
		return true

if __name__ == '__main__':
	from os import chdir
	from U6 import Config
	Config.read('pu6e.conf')
	chdir(Config.gamedir)
	from U6 import pal
	palette = pal.pal()
	palette.read(Config.gametype)
	tile.read()
	app = TileEditApp(0)
	app.MainLoop()
