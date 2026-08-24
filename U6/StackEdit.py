
from wx import *
from U6.util import index_ref, Bunch
from U6.ObjEdit import ObjPanel

#--------------------------------------------------------------------------

evtOBJECTUPDATED = NewEventType()

#def EVT_OBJECTLISTCHANGED( window, function ):
#	"""Your documentation here"""
#	window.Connect( -1, -1, OBJECTLISTCHANGED, function )

class ObjectUpdatedEvent(PyCommandEvent):
	eventType = evtOBJECTUPDATED
	def __init__(self, windowID, data=None):
		PyCommandEvent.__init__(self, self.eventType, windowID)
		self.__data = data

	def Clone( self ):
		self.__class__( self.GetId() )

	def GetData(self):
		return self.__data

#---------------------------------------------------------------------------

class MyTreeCtrl(TreeCtrl):
	def __init__(self, parent, id, pos, size, style):
		TreeCtrl.__init__(self, parent, id, pos, size, style)
		if Platform == '__WXMSW__':
			EVT_CHAR(self, parent.OnChar)

	def OnCompareItems(self, item1, item2):
		t1 = self.GetItemText(item1)
		t2 = self.GetItemText(item2)
		print(('compare: ' + t1 + ' <> ' + t2 + '\n'))
		if t1 < t2: return -1
		if t1 == t2: return 0
		return 1

	# Copy all children of src into node dst, including associated item data.
	# Does not currently copy images.
	# FIXME Does not check for recursion (!)
	def copy_recursive(self, src, dst):
		t = self
		# Warning: GetFirstChild does not complain if you do not provide
		# the 2nd argument, but will segfault.
		child, cookie = t.GetFirstChild(src, 0)
		while child.IsOk():
			name = t.GetItemText(child)
			data = t.GetItemData(child).GetData()
			new_child = t.AppendItem(dst, name)
			t.SetPyData(new_child, data)
			if t.ItemHasChildren(child):   # not strictly necessary to check
				self.copy_recursive(child, new_child)
			child, cookie = t.GetNextChild(src, cookie)

	# Finds an object, searching all children of parent.
	def find_object(self, o, parent):
		t = self
		child, cookie = t.GetFirstChild(parent, 0)
		while child.IsOk():
			data = t.GetItemData(child).GetData()
			if data is o:
				return child
			if t.ItemHasChildren(child):
				subitem = self.find_object(o, child)
				if subitem is not None:
					return subitem
			child, cookie = t.GetNextChild(parent, cookie)
		return None

#---------------------------------------------------------------------------

class StackFrame(Frame):
	def __init__(self, parent, id, title):
		# Use the WANTS_CHARS style so the panel doesn't eat the Return key.
		# Should I check for valid parent here and adjust FLOAT style?
		# Tab traversal doesn't work here yet.
		Frame.__init__(self, parent, id, title, style=FRAME_FLOAT_ON_PARENT|DEFAULT_FRAME_STYLE, size=Size(400,200))
		ID_STACK = NewIdRef()
		ID_OBJ   = NewIdRef()

		self.updated_cb = None
		self.objpanel   = ObjPanel(self, ID_OBJ)
		self.stackpanel = StackPanel(self, ID_STACK)
		self.objpanel.updated_cb = self.stackpanel.received_update   # nasty
		self.stackpanel.objpanel = self.objpanel
		if Platform == '__WXGTK__':
			self.objpanel.refocus = self.stackpanel  # NASTY!
		self.hbox=BoxSizer(HORIZONTAL)
		self.hbox.Add(self.stackpanel, 1, EXPAND)
		self.hbox.Add(self.objpanel,   0, EXPAND)
		self.SetSizer(self.hbox)
		EVT_COMMAND(self, -1, evtOBJECTUPDATED, self.OnObjectUpdated)

		# aliases
		self.set_default_obj = self.stackpanel.set_default_obj

	def set_point(self, *args):
		self.stackpanel.set_point(*args)
		# self.stackpanel.SetFocus()

	def OnObjectUpdated(self, evt):
		# print "object update event received!"
		if self.updated_cb:
			# Someone may want to be notified of the update.
			self.updated_cb(evt.GetData())

class StackPanel(Panel):
	def __init__(self, parent, id):
		Panel.__init__(self, parent, id, style=WANTS_CHARS) #|SUNKEN_BORDER)
		tID = NewIdRef()
		ID_CLIP = NewIdRef()

		self.tree = MyTreeCtrl(self, tID, DefaultPosition, DefaultSize,
                               TR_HAS_BUTTONS
                               #| TR_EDIT_LABELS
		                       #| TR_MULTIPLE
		                       #| TR_HIDE_ROOT
		                       | TR_FULL_ROW_HIGHLIGHT
		                       | TR_LINES_AT_ROOT
		                       | SUNKEN_BORDER
		                       )

		self.clipstatus = StaticText(self, ID_CLIP, "Clipboard: empty")

		self.vbox=BoxSizer(VERTICAL)
		self.vbox.Add(self.tree, 1, EXPAND)
		self.vbox.Add(self.clipstatus, 0, EXPAND|ALL, 3)
		self.SetSizer(self.vbox)

		# The objpanel must have the following methods:
		# display(obj)
		self.objpanel = None
		self.wx, self.wy, self.wz = None, None, None
		self.clipboard = None
		self.default_obj = None

		#import images
		#il = ImageList(16, 16)
		#idx1 = il.Add(images.getSmilesBitmap())
		#idx2 = il.Add(images.getOpenBitmap())
		#idx3 = il.Add(images.getNewBitmap())
		#idx4 = il.Add(images.getCopyBitmap())
		#idx5 = il.Add(images.getPasteBitmap())

		#self.tree.SetImageList(il)
		#self.il = il

		# NOTE:  For some reason tree items have to have a data object in
		#		order to be sorted.  Since our compare just uses the labels
		#		we don't need any real data, so we'll just use None.

		#EVT_SIZE(self, self.OnSize)
		EVT_TREE_ITEM_EXPANDED  (self, tID, self.OnItemExpanded)
		EVT_TREE_ITEM_COLLAPSED (self, tID, self.OnItemCollapsed)
		EVT_TREE_SEL_CHANGED	(self, tID, self.OnSelChanged)
		EVT_TREE_ITEM_ACTIVATED (self, tID, self.OnActivate)

		EVT_LEFT_DCLICK(self.tree, self.OnLeftDClick)
		EVT_RIGHT_DOWN(self.tree, self.OnRightClick)

		EVT_TREE_BEGIN_DRAG(self, tID, self.OnBeginDrag)
		EVT_TREE_END_DRAG(self, tID, self.OnEndDrag)

		# MSW cannot intercept the key in TREE_KEY_DOWN--it always
		# gets passed to the tree, regardless of event.Skip.  Instead,
		# we redirect the tree's EVT_CHAR to our OnChar (see the tree ctrl).
		if Platform != "__WXMSW__":
			EVT_TREE_KEY_DOWN(self, tID, self.OnKeyDown)

		self.tree.SetFocus()


	def OnBeginDrag(self, event):
		d = event.GetItem()
		if d != self.tree.GetRootItem():
			self.dragged = d
			event.Allow()

	def OnEndDrag(self, event):
		t = self.tree
		src = self.dragged
		dest = event.GetItem()

		if src == dest:
			# Can't drop node on itself.
			return 0

		src_parent = t.GetItemParent(src)
		src_data = t.GetItemData(src)
		src_obj = src_data.GetData()
		if dest.IsOk():
			dst_parent = t.GetItemParent(dest)
		else:
			# If destination is invalid, pretend we're appending to the root node.
			dest = t.GetLastChild(self.root)
			dst_parent = self.root

		src_name = t.GetItemText(src)
		dst_name = t.GetItemText(dest)

		#src_parent_name = t.GetItemText(src_parent)
		#dst_parent_name = t.GetItemText(dst_parent)
		rect = t.GetBoundingRect(dest)
		# The point is relative to the tree, while the bounding rect is relative
		# to the window.
		point = event.GetPoint()

		# --- FIXME!!! ---
		# Unfortunately, there's no way to get the logical coordinates of
		# the TreeCtrl!!  So we hardcode it.
   #	point = t.CalcScrolledPosition(*point)
		point[0] -= t.GetScrollPos(HORIZONTAL) * 10
		point[1] -= t.GetScrollPos(VERTICAL) * 10
		# ----------------

		print("- dragging from %s (%s) to %s" % (src_name, src_obj, dst_name))

		yoffset = point.y - rect.y

		if yoffset < 0 or yoffset > rect.height:
			# Shouldn't happen, but just in case.  It's okay if the
			# dest parent is the root node, because dropping to whitespace
			# is considered dropping on the root.
			if dst_parent != self.root:
				print("Clicked point not inside item rectangle!")
				return 0

		ratio = yoffset * 1.0 / rect.height

		if ratio < .20:
			left_sibling = t.GetPrevSibling(dest)
		elif ratio > .80:
			left_sibling = dest
		else:
			# The dropped-on node becomes the new parent.
			# Insert after its last child (if any).
			left_sibling = t.GetLastChild(dest)
			# Reparent the node, for the code below.
			dst_parent = dest

		# Check that we're not performing a recursive move.
		p = dst_parent
		while p.IsOk():
			if p == src:
				# Tried to copy src to somewhere under src.
				return 0
			p = t.GetItemParent(p)

		new_node = t.InsertItem(dst_parent, left_sibling, src_name)
		t.Expand(dst_parent)

		# The tree does not provide node-copy operations, so
		# we have to copy attributes (data, etc.) by hand.
		t.SetPyData(new_node, src_obj)

		src_parent_obj = t.GetItemData(src_parent).GetData()
		dst_parent_obj = t.GetItemData(dst_parent).GetData()

		# Grab any left sibling object data before we delete the node.
		# Call will safely return None if left_sibling is invalid.
		# Note: apparently left_sibling_obj can be obtained even after the
		# node is deleted.
		# FIXME Although this section is highly redundant with the
		# cut/paste functions, ordering of operations is a bit trickier
		# here.  E.g. since the src tree isn't deleted right away,
		# the user may cause the src node to be the left_sibling.
		# When src is deleted before moving, the left_sibling ceases
		# to exist.
		left_sibling_obj = t.GetItemData(left_sibling).GetData()

		# Copy everything under src node to the new node, and
		# delete the src node.
		t.copy_recursive(src, new_node)
		t.Delete(src)

		# The drag code is generic up to this point, but now
		# we mess around with the Objs linked to the dragged nodes.

		if left_sibling_obj is not None:
			# Search the container for the left sibling.
			try:
				sib_index = index_ref(dst_parent_obj, left_sibling_obj)
			except ValueError as s:
				# Object not found--serious error.
				print("--- debug [%s] ---" % s)
				print("left sibling", left_sibling_obj, "dest parent", dst_parent_obj)
				print("left sibling id", id(left_sibling_obj))
				print("dest ids", [ id(o) for o in dst_parent_obj ])
				print("------------------")
				raise ValueError("left sibling not found in destination parent")
		else:
			sib_index = -1

		# Delete src object from src parent container.  This must be done
		# -before- we add it to the dest parent container; otherwise we may
		# not delete the right object when src and dest parent are the same.
		d = index_ref(src_parent_obj, src_obj)
		del src_parent_obj[d]
		# Add source object after left_sibling, or before any siblings
		# if left_sibling is invalid (just like InsertItem does).
		dst_parent_obj.insert(sib_index + 1, src_obj)

		self.was_updated()

	def was_updated(self):
		# Send an ObjectUpdatedEvent out.
		data = Bunch(wx=self.wx, wy=self.wy, wz=self.wz)
		event = ObjectUpdatedEvent( self.GetId(), data )
		self.GetEventHandler().AddPendingEvent( event )

	# Callback function for the objpanel.  Finds the node containing the
	# updated object (if possible) and updates its textual description.
	def received_update(self, o):
		item = self.tree.find_object(o, self.root)
		if item is None:
			self.rebuild()    # Couldn't find object; rebuild to be safe.
		else:
			self.tree.SetItemText(item, o.name())  # Just update the name.
		self.was_updated()

	def OnRightClick(self, event):
		pass

	def OnLeftDClick(self, event):
		pass

	def OnSize(self, event):
		w,h = self.GetClientSizeTuple()
		self.tree.SetDimensions(0, 0, w, h)

	def OnItemExpanded(self, event):
		item = event.GetItem()
		#print("OnItemExpanded: %s\n" % self.tree.GetItemText(item))

	def OnItemCollapsed(self, event):
		item = event.GetItem()
		#print("OnItemCollapsed: %s\n" % self.tree.GetItemText(item))

	def OnSelChanged(self, event):
		self.item = event.GetItem()
		if self.item != self.root:   # Make sure this is not the root.
			o = self.tree.GetItemData(self.item).GetData()
			if self.objpanel:
				self.objpanel.display(o)
				# self.SetFocus()
		event.Skip()

	def OnActivate(self, event):
		pass

	def OnChar(self, event):
		if self._process_key(event):
			event.Skip()

	# Process key event.  Return 1 if we should skip the event, 0 if not.
	def _process_key(self, event):
		t = self.tree
		# Apparently GetItem() does -not- return the item you pressed the key on;
		# I consider this bad behavior.
		item = t.GetSelection()   # Returns 0 if no selection.
		key = event.GetKeyCode()

		# I check for 'S' up here because I want it to succeed regardless
		# of item selection.
		if key < 256 and chr(key).upper() == 'S' or key == 27:
			self.GetParent().Hide()
			return

		if not item or not item.IsOk():
			return

		if key == WXK_DELETE:
			self.delete_node(item)
		elif key == WXK_INSERT:
			if event.ShiftDown():
				self.create_node(item, 1)   # second parameter is obsolete now
			else:
				self.create_node(item, 0)
		elif key < 256:
			key = chr(key).upper()   # upper because tree control sends a -translated- char!
			if key == 'X':
				self.cut_node(item)
			elif key == 'C':
				self.copy_node(item)
			elif key == 'V':
				if event.ShiftDown():
				   self.paste_node(item, 1)   # Shift down, paste before
				else:
				   self.paste_node(item, 0)   # No modifiers, paste after
			elif key == 'N':
				self.create_node(item)
			elif key == '>' or key == '.' or key == 'B' or key == chr(22):  # ctrl-v
				self.paste_node_into(item)
			# FIXME The (Python?) treectrl will crash if no node is selected
			# and an unhandled alphanumeric key gets through.  So we only allow
			# stuff that's handled by the tree control.
			elif key in ('+', '-', '*'):
				return 1  # Skip event
		else:
			return 1

	def OnKeyDown(self, event):
		key_event = event.GetKeyEvent()
		if self._process_key(key_event):
			event.Skip()  # We skip the Tree event, not the key event.

	# Create a default object.  Formerly pasted it into the world, but
	# now creates it on the clipboard.
	def create_node(self, node, before=0):
		o = self.default_obj
		if not o: return None
		o = o.clone()
		if not o: return None
		self.push_clipboard(o)
		# self.paste_node(node, before)
		print("- created default object", o, "on clipboard")

	# Delete node and update object data; return object that was deleted.
	def delete_node(self, item):
		if item == self.root:
			return None   # Can't delete root node.
		t = self.tree
		o_src	= t.GetItemData(item).GetData()
		o_parent = t.GetItemData(t.GetItemParent(item)).GetData()
		i = index_ref(o_parent, o_src)
		del o_parent[i]
		t.Delete(item)
		self.was_updated()
		return o_src

	def cut_node(self, node):
		o = self.delete_node(node)
		if o:
			self.push_clipboard(o)
			print("- cut", o, "to clipboard")
		return o

	def copy_node(self, node):
		if node == self.root:
			return None   # Can't delete root node.
		t = self.tree
		o = t.GetItemData(node).GetData()
		c = o.clone()   # May return None
		if c is not None:
			self.push_clipboard(c)
			print("- copied", o, "to clipboard")
		else:
			print("- cannot copy object", o)

	# Paste node from clipboard into tree.
	# You can insert either before or after the target node.
	def paste_node(self, dest, before=0):
		t = self.tree

		if dest == self.root:
			# root node: reparent ourselves underneath it.
			parent = dest
			dest = t.GetLastChild(dest)
		else:
			parent = t.GetItemParent(dest)
			if before:
				dest = t.GetPrevSibling(dest)

		self._paste(parent, dest)

	def paste_node_into(self, dest):
		t = self.tree
		self._paste(dest, t.GetLastChild(dest))

	# Paste from clipboard into parent with left sibling dest.  Helper function.
	def _paste(self, parent, left_sibling):
		o = self.pop_clipboard()
		if not o: return None
		self.create_node_from_obj(o, parent, left_sibling)
		self.tree.Expand(parent)  # May need to expand if pasting -into- parent node.
		print("- pasted", o)
		self.was_updated()

	def create_node_from_obj(self, o, parent, left_sibling):
		t = self.tree
		o_dest   = t.GetItemData(left_sibling).GetData()
		o_parent = t.GetItemData(parent).GetData()
		# Update objects
		if o_dest:
			try:
				sib_index = index_ref(o_parent, o_dest)   # pasted node becomes right sibling
			except ValueError as s:
				# Object not found--serious error.
				print("--- debug [%s] ---" % s)
				print("left sibling", left_sibling_obj, "dest parent", dst_parent_obj)
				print("left sibling id", id(left_sibling_obj))
				print("dest ids", [ id(o) for o in dst_parent_obj ])
				print("------------------")
				raise ValueError("left sibling not found in destination parent")
		else:
			sib_index = -1	# The destination is empty (childless parent)
		o_parent.insert(sib_index + 1, o)
		# Update tree
		# This part is similar to build()
		new_node = t.InsertItem(parent, left_sibling, o.name())
		t.SetPyData(new_node, o)
		self.recursive_add(new_node, o)
		t.Expand(new_node)

	# Rebuild the stack.  Call build rather than set_point, because we don't
	# want extraneous things such as item reselection to occur.
	def rebuild(self):
		self.build(self.point)

	# Build the stack, given a Point.
	def build(self, point):
		t = self.tree
		t.DeleteAllItems()
		self.root = t.AddRoot("%03x, %03x, %x" % point.coords)
		t.SetPyData(self.root, point)
		self.recursive_add(self.root, point)
		t.Expand(self.root)

	# External callers use this to set up the stack for a given point.
	# Technically, I no longer need the coordinates passed in, since they're in Point.
	def set_point(self, point, wx, wy, wz):
		t = self.tree
		if self.wx != wx or self.wy != wy or self.wz != wz or self.point != point:
			self.wx, self.wy, self.wz = wx, wy, wz
			self.point = point
			# We clear the objpanel so that we don't continue editing an object when
			# changing Points.  This is because updates coming from objpanel
			# are assumed to occur at the current Point, the point we send
			# back through our own update callbacks.
		   # self.objpanel.clear()

		self.build(self.point)
		t.SelectItem(t.GetLastChild(self.root))
		sel = t.GetSelection()
		if not sel or not sel.IsOk() or sel == self.root:
			# Selection was unsuccessful; clear the objpanel.
			self.objpanel.clear()

	def recursive_add(self, parent, objs):
		for o in objs:
			child = self.tree.AppendItem(parent, o.name())
			self.tree.SetPyData(child, o)
			if o.contains:
				self.recursive_add(child, o.contains)
				self.tree.Expand(child)

	def set_default_obj(self, o):
		self.default_obj = o

	# Push item onto clipboard, returning what was there before.
	def push_clipboard(self, o):
		self.clipstatus.SetLabel("Clipboard: %s" % o.name())
		c = self.clipboard
		self.clipboard = o
		return c

	# Pop item off clipboard, returning item
	def pop_clipboard(self):
		self.clipstatus.SetLabel("Clipboard: empty")
		c = self.clipboard
		self.clipboard = None
		return c

class StackEditor(object):
	def __init__(self, default_obj, cb=None, parent=None):
		self.frame = None
		self.cb = cb
		self.parent = parent
		self.default_obj = default_obj

	def create(self):
		self.frame = StackFrame(self.parent, -1, "Stack Editor")
		self.frame.updated_cb = self.cb
		self.frame.set_default_obj(self.default_obj)

	def Show(self, boolean=1):
		if not self.frame:
			self.create()
		self.frame.Show(boolean)

	def Hide(self):
		if self.frame:
			self.frame.Hide()

	def IsShown(self):
		if self.frame:
			return self.frame.IsShown()
		return 0

	def dummy_point(self):
		class Obj(object):
			def __init__(self, name):
				self.contains = []
				self.name = name

			def __repr__(self):
				return "<Obj \"%s\">" % self.name

			def name(self): return self.name

		point = []

		for c in range(5):
			o = Obj("%d" % c)
			for i in range(4):
				o.contains.append(Obj("%d-%d" % (c, i)))
			point.append(o)

		return point

	def set_point(self, point, wx, wy, wz):
		if self.frame:
			self.frame.SetTitle("Stack Editor (%03x, %03x, %x)" % (wx, wy, wz))
			return self.frame.set_point(point, wx, wy, wz)

class StackApp(App):
	def OnInit(self):
		class Obj(object): pass
		o = Obj()
		stackedit = StackEditor(o)
		stackedit.Show()
		from U6 import Point
		point = Point.Point(0x134, 0x16c, 0)
		stackedit.set_point(point, 0x134, 0x16c, 0)
		self.SetTopWindow(stackedit.frame)
		return true

if __name__ == '__main__':
	app = StackApp(0)
	app.MainLoop()
