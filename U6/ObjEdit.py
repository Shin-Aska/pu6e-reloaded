#!/usr/bin/env python

from wx import *
from wx.lib.intctrl import EVT_INT
from U6.HexCtrl import HexCtrl
from U6.wxutil import *

class ObjPanel(Panel):
	def __init__(self, parent, id):
		Panel.__init__(self, parent, id, size=Size(150,-1), style=SUNKEN_BORDER|TAB_TRAVERSAL|WANTS_CHARS)

		self.updated_cb = None
		self.obj = None
		# Window to focus on if one of our controls stubbornly wrests focus
		# away from the rightful owner (GTK).
		self.refocus = None

		ID_WEIGHT = NewIdRef()
		ID_QUALITY = NewIdRef()
		ID_QUANTITY = NewIdRef()
		ID_STATUS = NewIdRef()
		ID_FRAME = NewIdRef()
		ID_TYPE = NewIdRef()

		keys = ('S', chr(27))
		# Tab traversal occurs in the order controls are created (not added to the Sizer).
		self.type = SpinCtrl_close(self, ID_TYPE, keys, value="0", min=0, max=0x3ff)
		self.frame = SpinCtrl_close(self, ID_FRAME, keys, value="0", min=0)
		self.quantity = SpinCtrl_close(self, ID_QUANTITY, keys, value="0", min=0, max=255)
		self.quality = SpinCtrl_close(self, ID_QUALITY, keys, value="0", min=0, max=255)
		self.status = HexCtrl(self, ID_STATUS, min=0, max=0xFF, limited=1, style=TE_PROCESS_ENTER)
		self.weight = TextCtrl(self, ID_WEIGHT, style=TE_READONLY)

		for ctrl in (ID_QUALITY, ID_QUANTITY, ID_FRAME, ID_TYPE):
			EVT_SPINCTRL(self, ctrl, self.Updated)
			EVT_TEXT_ENTER(self, ctrl, self.Updated)   # for windows

		# EVT_INT( self, ID_STATUS, self.Updated)  # This may cause a segfault if you cut an
		                                           # object and then press down twice (?!)
		EVT_TEXT_ENTER(self, ID_STATUS, self.Updated)

		controls = [
		   ('Type',    self.type),
		   ('Frame',   self.frame),
		   ('Quantity',self.quantity),
		   ('Quality', self.quality),
		   ('Status',  self.status),
		   ('Weight',  self.weight),
		]

		self.vbox = BoxSizer(VERTICAL)
		if 0:
			for text, ctrl in controls:
				hbox = BoxSizer(HORIZONTAL)
				hbox.Add(StaticText(self, NewIdRef(), text, style=ALIGN_RIGHT), 1, ALIGN_CENTER | RIGHT, 5)
				hbox.Add(ctrl, 0)
				self.vbox.Add(hbox, 0, EXPAND | ALL, 5)
			self.SetSizer(self.vbox)

		else:
			self.gs = GridSizer(0, 2, 5, 5)
			for text, ctrl in controls:
				self.gs.Add(StaticText(self, NewIdRef(), text, style=ALIGN_RIGHT), 0, ALIGN_CENTER_VERTICAL | ALIGN_RIGHT)
				self.gs.Add(ctrl, 0, EXPAND)
			self.vbox.Add(self.gs, 0, EXPAND|ALL, 3)
			self.SetSizer(self.vbox)

	def display(self, obj):
		if not obj: return   # We get NoneType on MSW, sometimes
		self.set_weight(obj.weight_total() / 10.0)
		self.set_quality(obj.quality)
		self.set_quantity(obj.qty())
		self.set_status(obj.status)
		self.set_frame(obj.frame())
		self.set_type(obj.basetype())
		self.set_frame_limit(obj.num_frames())
		self.obj = obj

	def clear(self):
		self.obj = None
		self.set_weight(0)
		self.set_quality(0)
		self.set_quantity(0)
		self.set_status(0)
		self.set_type(0)
		self.set_frame(0)
		self.set_frame_limit(0)

	def set_weight(self, w):
		self.weight.SetValue("%s stones" % w)

	def set_quality(self, q):
		self.quality.SetValue(q)

	def set_quantity(self, q):
		self.quantity.SetValue(q)

	def set_status(self, s):
		self.status.SetValue(s)

	def set_frame(self, f):
		self.frame.SetValue(f)

	def set_type(self, f):
		self.type.SetValue(f)

	def set_frame_limit(self, limit):
		if Platform == "__WXGTK__":
			# Checking platform here is probably overkill, but I'm tired of troubleshooting
			# bugs between MSW and GTK.
			f = Window.FindFocus()
		else:
			f = None
		if limit <= 0: limit = 1   # So that MSW does not show a negative upper limit (!!)
		self.frame.SetRange(0, limit - 1, self.refocus)   # Under GTK, this obtains focus (!)
		if f and self.refocus is None:
			# Set the focus to the old focused window, if we don't have an explicitly requested focus.
			# Apparently, GTK can reliably detect when our panel's controls were focused, but it
			# can't always tell when the stackpanel was focused.
			f.SetFocus()

	def close(self):
		self.GetParent().Hide()

	def Updated(self, evt):
		r = self.refocus
		# Disable explicit refocusing during an update.  Otherwise, we'll get forced back
		# to the stackpanel after any keyboard change to our controls.
		self.refocus = None
		o = self.obj
		if o:
			o.quantity = self.quantity.GetValue()
			o.quality  = self.quality.GetValue()
			o.status  = self.status.GetValue()
			o.set_type(self.type.GetValue())   # This will zero out the object's frame temporarily.
			self.set_frame_limit(o.num_frames())
			o.set_frame(self.frame.GetValue())
			self.set_weight(o.weight_total() / 10.0)
			if self.updated_cb:
				self.updated_cb(o)   # Signal an update of this object.

		self.refocus = r

class ObjFrame(Frame):
	def __init__(self, parent, ID, title):
		Frame.__init__(self, parent, ID, title, DefaultPosition, Size(250, 250))
		self.panel = ObjPanel(self, NewIdRef())

class ObjEditApp(App):
	def OnInit(self):
		frame = ObjFrame(None, NewIdRef(), "Object Editor")
		frame.Show()
		self.SetTopWindow(frame)
		return True

if __name__ == '__main__':
	app = ObjEditApp(0)
	app.MainLoop()
