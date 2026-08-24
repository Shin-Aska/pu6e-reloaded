from wx import *

# Enhanced spin control that will issue a close() call to the parent
# if a given key is pressed.  It also overrides the SetRange
# method to focus sanely in GTK, and keep the value within
# the limits in Windows.
class SpinCtrl_close(SpinCtrl):
	def __init__(self, parent, id, keys, *args, **kwargs):
		SpinCtrl.__init__(self, parent, id, *args, **kwargs)
		self.keys = keys
		EVT_CHAR(self, self.OnChar)

	def OnChar(self, event):
		key = event.GetKeyCode()
		if key < 256:
			key = chr(key).upper()
			if key in self.keys:
				self.GetParent().close()
				return
		event.Skip()

	def SetRange(self, min, max, focus=None):
		SpinCtrl.SetRange(self, min, max)
		# The windows spin control doesn't update the value
		# if the limit changes and a boundary is exceeded.
		if Platform == '__WXMSW__':
			v = self.GetValue()
			if v > max:
				self.SetValue(max)
			elif v < min:
				self.SetValue(min)
		# Under GTK, SetRange obtains focus (!!)  The only way
		# to set focus back to the original control is to do it
		# manually (you can't get the old focus reliably).
		if focus:
			focus.SetFocus()


class SpinCtrl_event(SpinCtrl):
	"""Like a SpinCtrl, but sends an update event when its SetValue method is called."""
	def SetValue(self, val):
		"""Set spin value; send update event if old and new values differ."""
		old = self.GetValue()
		SpinCtrl.SetValue(self, val)
		new = self.GetValue()
		if new != old:
			event = PyCommandEvent(wxEVT_COMMAND_SPINCTRL_UPDATED, self.GetId())
			event.SetEventObject(self)
			event.SetInt(new)
			self.GetEventHandler().ProcessEvent(event)
