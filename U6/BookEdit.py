#!/usr/bin/env python

from wx import *
from .wxutil import SpinCtrl_event
import os
from U6 import book

ID_TEXT  = 101
ID_SPIN  = 102

class BookFrame(Frame):
	def __init__(self, parent, ID, title):
		Frame.__init__(self, parent, ID, title, DefaultPosition, Size(250, 250))

		self.spin = SpinCtrl_event(self, ID_SPIN, value="-1", min=-1, max=book.num_books() - 1)
		self.text = TextCtrl(self, ID_TEXT, style=TE_MULTILINE)

		EVT_SPINCTRL(self, ID_SPIN, self.OnSpin)
		EVT_TEXT_ENTER(self, ID_SPIN, self.OnSpin)

		self.vbox=BoxSizer(VERTICAL)
		self.vbox.Add(self.spin, 0, EXPAND)
		self.vbox.Add(self.text, 1, EXPAND)
		self.SetSizer(self.vbox)

	def OnSpin(self, evt):
		self.text.SetValue(book.contents(evt.GetInt()))

class BookEditor(object):
	def __init__(self):
		# Frame will be created upon Show().
		self.frame = None

	def set_book(self, book):
		# The text field won't be updated if the values are equal, which may
		# be a problem for the first call.
		self.frame.spin.SetValue(book)

	def create(self):
		self.frame = BookFrame(None, -1, "Book Editor")
		# Set the book number (since we don't currently preserve it
		# across instances).
		self.set_book(0)

	def Show(self, *args):
		if not self.frame:
			self.create()
		self.frame.Show(*args)

	def IsShown(self):
		if self.frame:
			return self.frame.IsShown()
		else:
			return 0

class BookApp(App):
	def OnInit(self):
		bookedit = BookEditor()
		bookedit.Show()
		self.SetTopWindow(bookedit.frame)
		return True

if __name__ == '__main__':
	book.read()
	app = BookApp(0)
	app.MainLoop()
