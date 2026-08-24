
from wx import *
from U6.wxutil import SpinCtrl_close

class ChunkFrame(Frame):
	def __init__(self, parent, id, title, Map):
		# Use the WANTS_CHARS style so the panel doesn't eat the Return key.
		# Should I check for valid parent here and adjust FLOAT style?
		# Tab traversal doesn't work here yet.
		Frame.__init__(self, parent, id, title, style=FRAME_FLOAT_ON_PARENT|DEFAULT_FRAME_STYLE)
		ID_CHUNK = NewIdRef()

		self.mapchunk = None
		self.Map = Map
		self.coords = None

		self.chunknum = SpinCtrl_close(self, ID_CHUNK, ('C', chr(27)), value="0", min=0, max=1023)

		self.vbox=BoxSizer(VERTICAL)
		self.hbox=BoxSizer(HORIZONTAL)
		self.hbox.Add(StaticText(self, -1, "Chunk #"), 0, ALIGN_CENTER|RIGHT, 5)
		self.hbox.Add(self.chunknum, 1, EXPAND)
		self.vbox.Add(self.hbox, 0, EXPAND|ALL, 5)
		self.SetSizer(self.vbox)
		self.Fit()
		self.chunknum.SetFocus()

		EVT_SPINCTRL(self, ID_CHUNK, self.Updated)
		EVT_TEXT_ENTER(self, ID_CHUNK, self.OnTextEnter)

	def OnTextEnter(self, event):
		# Windows does not send a spinctrl event upon Enter, even though
		# the control's value -is- updated.  Note: GTK will not receive
		# the TextEnter event (which is fine) because the PROCESS_ENTER
		# style is not set on the control.
		self.Updated(None)

	def set_mapchunk(self, wx, wy, wz):
		c, tx, ty = self.Map.world_to_chunk_num(wx, wy, wz)
		self.coords = wx-tx, wy-ty, wz
		self.chunknum.SetValue(c)
		self.SetTitle("Chunk (%03x, %03x, %d)" % self.coords)

	def Updated(self, evt):
		if self.coords:
			c = self.chunknum.GetValue()
			self.Map.set_chunk_at(c, *self.coords)

	def close(self):
		self.Hide()

class ChunkEditor(object):
	def __init__(self, parent, Map):
		self.frame = None
		self.Map = Map
		self.parent = parent

	def create(self):
		self.frame = ChunkFrame(self.parent, -1, "Chunk (None)", self.Map)

	def Show(self, boolean):
		if not self.frame:
			self.create()
		self.frame.Show(boolean)

	def IsShown(self):
		if self.frame:
			return self.frame.IsShown()
		return 0

	def set_mapchunk(self, *args):
		if self.frame:
			self.frame.set_mapchunk(*args)

class ChunkApp(App):
	def OnInit(self):
		frame = ChunkFrame(None, -1, "Chunk Editor", Map)
		frame.Show()
		self.SetTopWindow(frame)
		return True

if __name__ == '__main__':
	from . import Map
	app = ChunkApp(0)
	app.MainLoop()
