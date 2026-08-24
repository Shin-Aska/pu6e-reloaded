from wx import *
from U6.HexCtrl import HexCtrl

# HexCtrl-derived class that selects/deselects text on focus/defocus.
class HexCtrl_focus(HexCtrl):
	def __init__(self, *args, **kwargs):
		HexCtrl.__init__(self, *args, **kwargs)
		EVT_SET_FOCUS(self, self.OnFocus)
		EVT_KILL_FOCUS(self, self.OnLostFocus)

	def OnFocus(self, event):
		# This only works for keyboard, but that's what I want.
		HexCtrl.SetSelection(self, -1, -1)
		event.Skip()

	def OnLostFocus(self, event):
		HexCtrl.SetSelection(self, 0, 0)
		event.Skip()

class GoToDialog(Dialog):
	def __init__(self, parent, coords=None):
		Dialog.__init__(self, parent, -1, "Go to...", style=CAPTION | SYSTEM_MENU | THICK_FRAME)
		sizer = BoxSizer(VERTICAL)
		gs = GridSizer(3, 2, 5, 5)
		x = HexCtrl_focus(self, NewIdRef(), min=0, max=0x3ff, limited=1)
		y = HexCtrl_focus(self, NewIdRef(), min=0, max=0x3ff, limited=1)
		z = HexCtrl_focus(self, NewIdRef(), min=0, max=5,     limited=1)

		self.controls = ( ('x', x), ('y', y), ('z', z) )
		for text, ctrl in self.controls:
			gs.Add(StaticText(self, NewIdRef(), text, style=ALIGN_RIGHT), 0, ALIGN_CENTER_VERTICAL | ALIGN_RIGHT)
			gs.Add(ctrl, 0, EXPAND)
		sizer.Add(gs, 0, EXPAND|ALL, 3)

		if coords:
			x.SetValue(coords[0])
			y.SetValue(coords[1])
			z.SetValue(coords[2])

		# Add OK/Cancel buttons
		line = StaticLine(self, -1, style=LI_HORIZONTAL)
		sizer.Add(line, 0, GROW|ALIGN_CENTER_VERTICAL|ALL, 5)

		box = BoxSizer(HORIZONTAL)

		btn = Button(self, ID_OK, " OK ")
		btn.SetDefault()
		box.Add(btn, 1, ALIGN_CENTRE|ALL, 5)
		btn = Button(self, ID_CANCEL, " Cancel ")
		box.Add(btn, 1, ALIGN_CENTRE|ALL, 5)
		sizer.Add(box, 0, EXPAND|ALL, 5)
		self.SetSizer(sizer)
		sizer.Fit(self)

	def Values(self):
		return [ ctrl.GetValue() for text, ctrl in self.controls ]


class GoToApp(App):
	def OnInit(self):
		d = GoToDialog(None)
		val = d.ShowModal()
		if val == ID_OK:
			print(d.Values())
		d.Destroy()
		return True

if __name__ == '__main__':
	app = GoToApp(0)
	app.MainLoop()
