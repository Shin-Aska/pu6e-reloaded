#!/usr/bin/env python

from wx import *
import mapedit_gl
from U6.BookEdit import BookEditor
from U6.StackEdit import StackEditor
from U6.ChunkEdit import ChunkEditor
from U6.TileEdit import TileEditor
from U6.GoTo import GoToDialog
from U6 import book, Map, obj, U6util, Config, NPCs, tile, look
import copy

render = mapedit_gl

# The App class will pop up a dialog box if these
# imports fail.
try:
	from wx.glcanvas import *
	haveGLCanvas = 1
except ImportError:
	haveGLCanvas = 0

try:
	from OpenGL.GL import *
	haveOpenGL = 1
except ImportError:
	haveOpenGL = 0

#----------------------------------------------------------------------


class MapFrame(Frame):
	def __init__(self, parent, ID, title, size):
		Frame.__init__(self, parent, ID, title, DefaultPosition, size)

		self.fullscreen_hides_menubar = 1
		self.bookedit = BookEditor()
		self.stackedit = StackEditor(obj.default_object(), self.object_updated, self)
		self.stackedit.create()  # Explicitly create the StackEditor just so it will
		                         # accept updates right away.

		self.chunkedit = ChunkEditor(self, Map)
		self.tileedit  = TileEditor(self, render.palette, look.get_obj_name)
		self.menubar = self.create_menu()
		self.SetMenuBar(self.menubar)

		self.statusbar = None
		#self.statusbar = self.CreateStatusBar(1, ST_SIZEGRIP)
		#self.HideStatusBar()

		self.canvas = MapCanvas(self, self.stackedit, self.chunkedit, self.tileedit)
		self.vbox=BoxSizer(VERTICAL)
		self.vbox.Add(self.canvas,1,EXPAND)
		self.SetSizer(self.vbox)
		self.canvas.SetFocus()

	def object_updated(self, data):
		#print "map window: object was updated at %03x, %03x, %03x" % (data.wx, data.wy, data.wz)
		obj.updated_at(data.wx, data.wy, data.wz)

	def create_menu(self):

		self.ID_ABOUT = NewIdRef()
		self.ID_FILE_SAVE = NewIdRef()
		self.ID_FILE_QUIT = NewIdRef()
		self.ID_VIEW_ANIMATE = NewIdRef()
		self.ID_VIEW_PALETTE = NewIdRef()
		self.ID_VIEW_HYBRID = NewIdRef()
		self.ID_VIEW_OBJECTS = NewIdRef()
		self.ID_VIEW_GRID = NewIdRef()
		self.ID_VIEW_LOCATION = NewIdRef()
		self.ID_VIEW_FULLSCREEN = NewIdRef()
		self.ID_VIEW_ZOOM_IN = NewIdRef()
		self.ID_VIEW_ZOOM_OUT = NewIdRef()
		self.ID_OPTIONS_TERRAIN = NewIdRef()
		self.ID_WINDOW_STACK = NewIdRef()
		self.ID_WINDOW_BOOK = NewIdRef()
		self.ID_WINDOW_CHUNK = NewIdRef()
		self.ID_WINDOW_TILE = NewIdRef()
		self.ID_WINDOW_GOTO = NewIdRef()

		menu_file = Menu()
		menu_view = Menu()
		menu_options = Menu()
		menu_window = Menu()
		menu_file.Append(self.ID_FILE_SAVE,    "&Save", "Save the world")
		menu_file.Append(self.ID_FILE_QUIT,    "&Quit", "Quit pu6e")
		menu_view.Append(self.ID_VIEW_ANIMATE, "&Animated tiles")
		menu_view.Append(self.ID_VIEW_PALETTE, "&Palette rotation")
		menu_view.Append(self.ID_VIEW_HYBRID,  "&Hybrid tiles")
		menu_view.Append(self.ID_VIEW_OBJECTS, "&Objects")
		menu_view.Append(self.ID_VIEW_GRID,    "&Grid")
		menu_view.Append(self.ID_VIEW_LOCATION, "&Location")
		menu_view.AppendSeparator()
		menu_view.Append(self.ID_VIEW_FULLSCREEN,    "&Fullscreen")
		menu_view.Append(self.ID_VIEW_ZOOM_OUT,   "Zoom O&ut")
		menu_view.Append(self.ID_VIEW_ZOOM_IN,    "Zoom &In")
		menu_options.Append(self.ID_OPTIONS_TERRAIN, "Edit &Terrain")
		menu_window.Append(self.ID_WINDOW_STACK,  "&Stack Editor")
		menu_window.Append(self.ID_WINDOW_CHUNK,  "&Chunk Editor")
		menu_window.Append(self.ID_WINDOW_TILE,  "&Tile Viewer")
		menu_window.Append(self.ID_WINDOW_BOOK,  "&Book Editor")
		menu_window.AppendSeparator()
		menu_window.Append(self.ID_WINDOW_GOTO,  "&Go to...")
		menuBar = MenuBar()
		menuBar.Append(menu_file, "&File");
		menuBar.Append(menu_view, "&View");
		menuBar.Append(menu_options, "&Options");
		menuBar.Append(menu_window, "&Window");

		EVT_MENU(self, self.ID_WINDOW_GOTO, self.GoTo)
		EVT_MENU(self, self.ID_FILE_SAVE, self.Save)
		EVT_MENU(self, self.ID_FILE_QUIT, self.Quit)

		for i in (self.ID_VIEW_ANIMATE, self.ID_VIEW_PALETTE, self.ID_VIEW_HYBRID,
		          self.ID_VIEW_OBJECTS, self.ID_VIEW_GRID, self.ID_VIEW_LOCATION,
				  self.ID_VIEW_FULLSCREEN, self.ID_OPTIONS_TERRAIN,
				  self.ID_WINDOW_STACK, self.ID_WINDOW_CHUNK,
				  self.ID_WINDOW_TILE, self.ID_WINDOW_BOOK):
			EVT_MENU(self, i, self.MenuChecked)
		for i in (self.ID_VIEW_ZOOM_IN, self.ID_VIEW_ZOOM_OUT):
			EVT_MENU(self, i, self.MenuCommand)
		return menuBar

	def MenuCommand(self, event):
		i = event.GetId()
		if i == self.ID_VIEW_ZOOM_IN:
			self.canvas.zoom(2.0)
		elif i == self.ID_VIEW_ZOOM_OUT:
			self.canvas.zoom(0.5)

	# Handle items that (should be) checkboxes.
	def MenuChecked(self, event):
		i = event.GetId()
		if i == self.ID_VIEW_LOCATION:
			render.display_coords ^= 1
		elif i == self.ID_VIEW_ANIMATE:
			render.animate_tiles ^= 1
		elif i == self.ID_VIEW_GRID:
			render.display_grid ^= 1
		elif i == self.ID_VIEW_OBJECTS:
			render.display_objects ^= 1
			if render.display_objects == 0: render.fade_objects = 1.0
		elif i == self.ID_VIEW_PALETTE:
			render.rotate_palette ^= 1
		elif i == self.ID_VIEW_FULLSCREEN:
			render.fullscreen ^= 1
			self.ShowFullScreen(render.fullscreen)
		elif i == self.ID_VIEW_HYBRID:
			render.hybrid_tiles ^= 1
		elif i == self.ID_WINDOW_STACK:
			self.stackedit.Show(not self.stackedit.IsShown())
		elif i == self.ID_WINDOW_CHUNK:
			self.chunkedit.Show(not self.chunkedit.IsShown())
		elif i == self.ID_WINDOW_TILE:
			self.tileedit.Show(not self.tileedit.IsShown())
		elif i == self.ID_WINDOW_BOOK:
			self.bookedit.Show(not self.bookedit.IsShown())
		elif i == self.ID_OPTIONS_TERRAIN:
			self.canvas.edit_terrain ^= 1

	def GoTo(self, event):
		c = render.get_centered_coords()
		dlg = GoToDialog(self, c)
		val = dlg.ShowModal()
		if val == ID_OK:
			wx, wy, wz = dlg.Values()
			self.canvas.set_coords(wx, wy, wz)
		dlg.Destroy()

	def Quit(self, event):
		sys.exit()
		self.Close(true)

	def Save(self, event):
		try:
			print("- Writing objects...")
			obj.write_changes()
			print("  Writing NPCs...")
			NPCs.write()
			print("  Writing map data...")
			Map.write_changes()
			print("- Done.")
		except:
			print("** Write failed!")
			raise

	def ShowMenuBar(self):
		self.SetMenuBar(self.menubar)

	def HideMenuBar(self):
		self.SetMenuBar(None)

	def ShowStatusBar(self):
		self.SetStatusBar(self.statusbar)

	def SetStatusText(self, *args, **kwargs):
		if self.statusbar:
			self.statusbar.SetStatusText(*args, **kwargs)

	def HideStatusBar(self):
		self.SetStatusBar(None)

	def ShowFullScreen(self, full):
		# The menu bar fails to disappear with GTK 2.4.0, so we remove it manually.
		# This should be fixed with 2.4.1 and above.
		if full == true:
			if self.fullscreen_hides_menubar:
				self.HideMenuBar()
				self.HideStatusBar()
		else:
			self.ShowMenuBar()
			self.ShowStatusBar()
		Frame.ShowFullScreen(self, full)

	def BookEdit(self, event):
		self.bookedit.Show()

class MyCanvasBase(GLCanvas):
	def __init__(self, parent):
		GLCanvas.__init__(self, parent, -1)
		self.init = false
		# initial mouse position
		self.lastx = self.x = 30
		self.lasty = self.y = 30
		EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		EVT_SIZE(self, self.OnSize)
		EVT_PAINT(self, self.OnPaint)
		EVT_LEFT_DOWN(self, self.OnLeftDown)  # needs fixing...
		EVT_LEFT_UP(self, self.OnLeftUp)
		EVT_MOTION(self, self.OnMouseMotion)

	def OnEraseBackground(self, event):
		pass # Do nothing, to avoid flashing on MSW.

	def OnSize(self, event):
		size = self.GetClientSize()
		self.ResizeGL(size.width, size.height)
		if self.GetContext():
			self.SetCurrent()

	def OnPaint(self, event):
		dc = PaintDC(self)
		self.SetCurrent()
		if not self.init:
			self.InitGL()
			self.init = true
		self.OnDraw()

	def OnMouseDown(self, evt):
#		self.CaptureMouse()
		pass

	def OnMouseUp(self, evt):
#		self.ReleaseMouse()
		pass

	def OnMouseMotion(self, evt):
		pass
		#if evt.Dragging() and evt.LeftIsDown():
		#	self.x, self.y = self.lastx, self.lasty
		#	self.x, self.y = evt.GetPosition()
		#	self.Refresh(false)

class MapCanvas(MyCanvasBase):
	def __init__(self, parent, stackedit, chunkedit, tileedit):
		MyCanvasBase.__init__(self, parent)
		self.dragging = None   # The object (and wx, wy, wz coordinates) we're dragging.
		self.rdragging = None   # Coordinates from which we're right dragging.
		self.timer = PyTimer(self.Notify)
		self.timer.Start(51)
		self.edit_terrain = 0
		self.stackedit = stackedit
		self.chunkedit = chunkedit
		self.tileedit = tileedit
		self.parent = parent

		#EVT_IDLE(self, self.OnIdle)
		EVT_KEY_DOWN(self, self.OnKeyDown)
		EVT_RIGHT_DOWN(self, self.OnRightDown)

	def InitGL( self ):
		render.InitGL(render.screen_width, render.screen_height)

	def ResizeGL(self, w, h):
		render.Resize(w, h)

	def OnDraw(self):
		render.draw()
		self.SwapBuffers()

	def OnIdle(self, event):
		render.tick()
		if render.game_timer > 2000: sys.exit()
		self.Refresh(false)       # Repaint GL canvas (without erasing bg)
		event.RequestMore(true)   # Call idle function repeatedly.

	def Notify(self):
		render.tick()
		#print render.game_timer
		#if render.game_timer > 500: sys.exit()
		self.Refresh(false)

	def OnKeyDownPlay(self, evt):
		key = evt.GetKeyCode()
		if evt.HasModifiers():
			evt.Skip()
			return

		avatar = NPCs.npcs[1]
		wx, wy, wz = avatar.x, avatar.y, avatar.z

		if key == WXK_NUMPAD4 or key == WXK_NUMPAD_LEFT:  wx -= 1
		if key == WXK_NUMPAD6 or key == WXK_NUMPAD_RIGHT: wx += 1
		if key == WXK_NUMPAD8 or key == WXK_NUMPAD_UP:    wy -= 1
		if key == WXK_NUMPAD2 or key == WXK_NUMPAD_DOWN:  wy += 1
		if key == WXK_NUMPAD7 or key == WXK_NUMPAD_HOME:  wx -= 1; wy -= 1
		if key == WXK_NUMPAD1 or key == WXK_NUMPAD_END:   wx -= 1; wy += 1
		if key == WXK_NUMPAD9 or key == WXK_NUMPAD_PRIOR: wx += 1; wy -= 1
		if key == WXK_NUMPAD3 or key == WXK_NUMPAD_NEXT:  wx += 1; wy += 1

		if key < 256:
			key = chr(key)
			if key == 'A':
				block = obj.world_to_block(wx, wy)
				print("avatar is at: (%03x,%03x,%03x) block %d" % (wx, wy, wz, block))
			if key == 'E':
				EVT_KEY_DOWN(self, self.OnKeyDown)   # doesn't work.

		if (avatar.x, avatar.y) != (wx, wy):
			# Avatar moved.
			print("moving avatar from (%03x,%03x) to (%03x,%03x)" % ( avatar.x, avatar.y, wx, wy ))
			if 1 or not U6util.blocked_at(wx, wy):
				if not obj.remove_object_at(avatar, avatar.x, avatar.y, avatar.z):
					pass
				avatar.x, avatar.y, avatar.z = wx, wy, wz
				obj.add_object_at(avatar, wx, wy, wz)
				self.set_coords(wx - 10, wy - 10, wz)   # need centering function

	def OnKeyDown(self, evt):
		key = evt.GetKeyCode()
		m = 8
		wx, wy, wz = render.get_centered_coords()

		if key == ord('G') and evt.ControlDown():  # ctrl-G
			self.GetParent().GoTo(None)
			return
		elif key == ord('T') and evt.ControlDown():  # ctrl-T
			self.edit_terrain ^= 1
			return
		elif key == ord('S') and evt.ControlDown():  # ctrl-S
			self.GetParent().Save(None)
			return
		elif evt.HasModifiers():
			evt.Skip()
			return

		if key < 256:  # alphanumeric
			key = chr(key)
			if key == 'Q':
				sys.exit()
			elif key == 'G':
				render.display_grid ^= 1
			elif key == '=' or key == '+':
				self.zoom(2.0)
			elif key == '-':
				self.zoom(0.5)
			elif key == 'O':
				render.display_objects ^= 1
				if render.display_objects == 0: render.fade_objects = 1.0
			elif key == 'A':
				render.animate_tiles ^= 1
			elif key == 'P':
				render.rotate_palette ^= 1
			elif key == 'L':
				render.display_coords ^= 1
			elif key == 'F':
				render.fullscreen ^= 1
				self.GetParent().ShowFullScreen(render.fullscreen)
			elif key == 'H':
				render.hybrid_tiles ^= 1
			elif key == 'E':
				EVT_KEY_DOWN(self, self.OnKeyDownPlay)
				print("set event key down")
			elif key == 'S':
				if self.stackedit.IsShown():
					self.stackedit.Hide()
				else:
					self.stackedit.Show()
			elif key == 'C':
				self.chunkedit.Show(not self.chunkedit.IsShown())
			elif key == 'T':
				self.tileedit.Show(not self.tileedit.IsShown())
			else:
				evt.Skip()
		else:  # "special" key
			if   key == WXK_LEFT:  wx -= 1
			elif key == WXK_RIGHT: wx += 1
			elif key == WXK_UP:    wy -= 1
			elif key == WXK_DOWN:  wy += 1
			# Windows does not distinguish between the numpad and other arrows.
			# So we require numlock to be enabled.
			elif key == WXK_NUMPAD4 or key == WXK_NUMPAD_LEFT:  wx -= m
			elif key == WXK_NUMPAD6 or key == WXK_NUMPAD_RIGHT: wx += m
			elif key == WXK_NUMPAD8 or key == WXK_NUMPAD_UP:    wy -= m
			elif key == WXK_NUMPAD2 or key == WXK_NUMPAD_DOWN:  wy += m
			elif key == WXK_NUMPAD7 or key == WXK_NUMPAD_HOME:  wx -= m; wy -= m
			elif key == WXK_NUMPAD1 or key == WXK_NUMPAD_END:   wx -= m; wy += m
			elif key == WXK_NUMPAD9 or key == WXK_NUMPAD_PRIOR: wx += m; wy -= m
			elif key == WXK_NUMPAD3 or key == WXK_NUMPAD_NEXT:  wx += m; wy += m
			elif key == WXK_NUMPAD5 or key == WXK_NUMPAD_BEGIN:
				wx, wy, wz = Map.adjust_coords_for_level(wx, wy, wz, wz+1)
			elif key == WXK_NUMPAD0 or key == WXK_NUMPAD_INSERT:
				wx, wy, wz = Map.adjust_coords_for_level(wx, wy, wz, wz-1)
			elif key == WXK_NUMPAD_ADD:      self.zoom(2.0)
			elif key == WXK_NUMPAD_SUBTRACT: self.zoom(0.5)
			else:
				evt.Skip()
			self.set_coords(wx, wy, wz)

	def OnLeftDown(self, evt):
		x, y = evt.GetPosition()
		wx, wy, wz = render.screen_to_world(x, y)

		if render.display_objects:
			lookable = U6util.lookable_at(wx, wy, wz)
		else:
			# Only show/drag maptiles if objects not displayed.
			lookable = None

		if lookable:
			print(U6util.object_description(lookable))
			self.dragging = (lookable, wx, wy, wz)
		else:
			name, parsed_name = U6util.get_tile_name(Map.maptile_at(wx, wy, wz))
			print("* Thou dost see " + parsed_name + ".")
			# This is so we can drag map chunks around.  Perhaps we should set the chunk
			# number ahead of time.
			self.dragging = (None, wx, wy, wz)

	def OnLeftUp(self, evt):
		x, y = evt.GetPosition()
		wx, wy, wz = render.screen_to_world(x, y)
		chunk = Map.world_to_chunk(wx, wy, wz)
		stackedit = self.stackedit

		print("world (%03x, %03x, %d) window [%d, %d]" % (wx, wy, wz, x, y), "chunk", chunk)

		# Drop handling: self.dragging will have been set in OnLeftDown.
		if self.dragging:
			o, ox, oy, oz = self.dragging
			self.dragging = None
		else:
			ox, oy, oz = wx, wy, wz

		if ox != wx or oy != wy or oz != wz:
			if evt.ShiftDown():
				# Chunk moved.
				c = Map.world_to_chunk_num(ox, oy, oz)[0]
				Map.set_chunk_at(c, wx, wy, wz)
			elif o:
				# Object moved.
				# Compensate for double-size objects.  If we don't want to rely
				# on the object's coordinates, then we'll need to calculate object
				# size here or return it in lookable_at (above).
				dx = o.x - ox; dy = o.y - oy
				add = None

				if evt.ControlDown():
					add = o.clone()
					if add is None:
						print("- Cannot copy object %s." % o)
				elif obj.remove_object_at(o, o.x, o.y, o.z):
					add = o

				if add:
					obj.add_object_at(add, wx+dx, wy+dy, wz)
				else:
					print("We lost the dragged object %s!  Cancelling drag." % o)
			else:
				# Maptile moved (no object set; no modifiers)
				if self.edit_terrain:
					t = Map.maptile_at(ox, oy, oz)
					Map.set_maptile_at(t, wx, wy, wz)

		else:
			# No motion (no dragging).  Don't do anything.
			pass

		# Now display what's at the point, and update the stack.
		t = Map.maptile_at(wx, wy, wz)
		name, parsed_name = U6util.get_tile_name(t)
		print("  maptile: %04x %s -> %s" % (t, name, parsed_name))
		self.tileedit.select_tile(t)

		objs = obj.objects_at(wx, wy, wz)
		U6util.output_objects(objs)

		# print "  blocked? %d" % U6util.blocked_at(wx, wy, wz)

		if objs is None:
			# FIXME We create a new point for every empty location.
			objs = obj.add_point_at(wx, wy, wz)
		stackedit.set_point(objs, wx, wy, wz)

		# Also, update the Chunk Editor.
		self.chunkedit.set_mapchunk(wx, wy, wz)

	def OnRightDown(self, evt):
		x, y = evt.GetPosition()
		wx, wy, wz = render.screen_to_world(x, y)
		t = self.tileedit.selected()
		if t is None: return
		Map.set_maptile_at(t, wx, wy, wz)
		self.rdragging = (wx, wy, wz)

	def OnMouseMotion(self, evt):
		if evt.Dragging() and evt.RightIsDown():
			t = self.tileedit.selected()
			if t is None: return
			x, y = evt.GetPosition()
			wx, wy, wz = render.screen_to_world(x, y)
			ox, oy, oz = self.rdragging
			if wx != ox or wy != oy or wz != oz:
				Map.set_maptile_at(t, wx, wy, wz)
				self.rdragging = (wx, wy, wz)

	def set_coords(self, wx, wy, wz):
		render.set_centered_coords(wx, wy, wz)
		# This is pretty expensive (10% CPU).
		self.GetParent().SetStatusText("(%03x, %03x, %d)" % tuple(render.coords))
		# SetTitle is still extremely expensive (like, 100% CPU).
		#self.GetParent().SetTitle("Map Editor (%03x, %03x, %d)" % tuple(render.coords))
		# We may perform a double refresh if animation is active.  The Perl
		# code does not refresh on movement, if animation active.
		# self.Refresh(false)

	# Zoom by factor. factor > 1 to zoom in, 0 < factor < 1 to zoom out.
	def zoom(self, factor):
		render.scale_factor *= factor
		render.Resize(render.screen_width, render.screen_height)  # can I trigger a resize event?

def FatalErrorDialog(msg):
	dlg = MessageDialog(None, msg, 'Fatal error', OK | ICON_INFORMATION)
	dlg.ShowModal()
	dlg.Destroy()
	sys.exit()

def run():
	class MyApp(App):
		def OnInit(self):
			if not haveGLCanvas:
				FatalErrorDialog('The GLCanvas has not been included with this build of Python!')
			elif not haveOpenGL:
				FatalErrorDialog('The PyOpenGL package is not installed.  You can get it at\n'
									  'http://PyOpenGL.sourceforge.net/.')

			frame = MapFrame(None, -1, "pu6e",
			                 Size(render.screen_width,render.screen_height))
			frame.Show(True)
			self.SetTopWindow(frame)
			return True

	app = MyApp(0)
	app.MainLoop()

def _main():
	print("Reading configuration file...")
	conf = Config
	conf.read('pu6e.conf')
	print("Reading data files...")
	render.read_data(conf.gamedir, conf.gametype)
	#import time
	#time.sleep(60)
	#sys.exit()
	#render.coords = [0x134, 0x16c]
	render.set_centered_coords(0x134, 0x16c, 0)
#	render.coords = [0x20, 0x20, 1]
	render.screen_width, render.screen_height = conf.screen_width, conf.screen_height
	render.scale_factor = conf.scale_factor
	run()

if __name__ == '__main__':
	_main()
