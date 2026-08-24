#!/usr/bin/env python

from wx import *
from wx.glcanvas import *
from OpenGL.GL import *

class MyCanvasBase(GLCanvas):
	def __init__(self, parent):
		GLCanvas.__init__(self, parent, -1)
		self.init = False
		# initial mouse position
		self.lastx = self.x = 30
		self.lasty = self.y = 30
		EVT_ERASE_BACKGROUND(self, self.OnEraseBackground)
		EVT_SIZE(self, self.OnSize)
		EVT_PAINT(self, self.OnPaint)
		EVT_LEFT_DOWN(self, self.OnMouseDown)  # needs fixing...
		EVT_LEFT_UP(self, self.OnMouseUp)
		EVT_MOTION(self, self.OnMouseMotion)

	def OnEraseBackground(self, event):
		pass # Do nothing, to avoid flashing on MSW.

	def OnSize(self, event):
		size = self.GetClientSize()
		if self.GetContext():
			self.SetCurrent()
			glViewport(0, 0, size.width, size.height)

	def OnPaint(self, event):
		dc = PaintDC(self)
		self.SetCurrent()
		if not self.init:
			self.InitGL()
			self.init = True
		self.OnDraw()

	def OnMouseDown(self, evt):
		self.CaptureMouse()

	def OnMouseUp(self, evt):
		self.ReleaseMouse()

	def OnMouseMotion(self, evt):
		if evt.Dragging() and evt.LeftIsDown():
			self.x, self.y = self.lastx, self.lasty
			self.x, self.y = evt.GetPosition()
			self.Refresh(False)

class TileCanvas(MyCanvasBase):
	def InitGL(self):
		# set viewing projection
		glMatrixMode(GL_PROJECTION);
		glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0);

		# position viewer
		glMatrixMode(GL_MODELVIEW);
		glTranslatef(0.0, 0.0, -2.0);

		# position object
		glRotatef(self.y, 1.0, 0.0, 0.0);
		glRotatef(self.x, 0.0, 1.0, 0.0);

		glEnable(GL_DEPTH_TEST);
		glEnable(GL_LIGHTING);
		glEnable(GL_LIGHT0);


	def OnDraw(self):
		# clear color and depth buffers
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

		# set viewing projection
		glMatrixMode(GL_PROJECTION);
		glLoadIdentity()
		glFrustum(-0.5, 0.5, -0.5, 0.5, 1.0, 3.0);

		# position viewer
		glMatrixMode(GL_MODELVIEW);
		glLoadIdentity()
		glTranslatef(0.0, 0.0, -2.0);

		# position object
		glRotatef(self.y, 1.0, 0.0, 0.0);
		glRotatef(self.x, 0.0, 1.0, 0.0);

		glEnable(GL_DEPTH_TEST);
		glEnable(GL_LIGHTING);
		glEnable(GL_LIGHT0);


		# draw six faces of a cube
		glBegin(GL_QUADS)
		glNormal3f( 0.0, 0.0, 1.0)
		glVertex3f( 0.5, 0.5, 0.5)
		glVertex3f(-0.5, 0.5, 0.5)
		glVertex3f(-0.5,-0.5, 0.5)
		glVertex3f( 0.5,-0.5, 0.5)

		glNormal3f( 0.0, 0.0,-1.0)
		glVertex3f(-0.5,-0.5,-0.5)
		glVertex3f(-0.5, 0.5,-0.5)
		glVertex3f( 0.5, 0.5,-0.5)
		glVertex3f( 0.5,-0.5,-0.5)

		glNormal3f( 0.0, 1.0, 0.0)
		glVertex3f( 0.5, 0.5, 0.5)
		glVertex3f( 0.5, 0.5,-0.5)
		glVertex3f(-0.5, 0.5,-0.5)
		glVertex3f(-0.5, 0.5, 0.5)

		glNormal3f( 0.0,-1.0, 0.0)
		glVertex3f(-0.5,-0.5,-0.5)
		glVertex3f( 0.5,-0.5,-0.5)
		glVertex3f( 0.5,-0.5, 0.5)
		glVertex3f(-0.5,-0.5, 0.5)

		glNormal3f( 1.0, 0.0, 0.0)
		glVertex3f( 0.5, 0.5, 0.5)
		glVertex3f( 0.5,-0.5, 0.5)
		glVertex3f( 0.5,-0.5,-0.5)
		glVertex3f( 0.5, 0.5,-0.5)

		glNormal3f(-1.0, 0.0, 0.0)
		glVertex3f(-0.5,-0.5,-0.5)
		glVertex3f(-0.5,-0.5, 0.5)
		glVertex3f(-0.5, 0.5, 0.5)
		glVertex3f(-0.5, 0.5,-0.5)
		glEnd()

		glRotatef((self.lasty - self.y)/100., 1.0, 0.0, 0.0);
		glRotatef((self.lastx - self.x)/100., 0.0, 1.0, 0.0);

		self.SwapBuffers()


class TilePanel(Panel):
	def __init__(self, parent, id):
		Panel.__init__(self, parent, id, style=SUNKEN_BORDER|TAB_TRAVERSAL|WANTS_CHARS)

		self.updated_cb = None
		self.tile = None

		self.tiles = TileCanvas(self)
		self.vbox=BoxSizer(VERTICAL)
		self.vbox.Add(self.tiles, 1, EXPAND)
		self.SetSizer(self.vbox)

class TileFrame(Frame):
	def __init__(self, parent, ID, title):
		Frame.__init__(self, parent, ID, title, DefaultPosition, Size(250, 250))
		self.panel = TilePanel(self, NewIdRef())

class TileEditor(object):
	def __init__(self, parent):
		self.frame = None
		self.parent = parent

	def create(self):
		self.frame = TileFrame(self.parent, -1, "Tile Editor")

	def Show(self, boolean=1):
		if not self.frame:
			self.create()
		self.frame.Show(boolean)

	def IsShown(self):
		if self.frame:
			return self.frame.IsShown()
		return 0

#	def set_mapchunk(self, *args):
#		if self.frame:
#			self.frame.set_mapchunk(*args)

class TileEditApp(App):
	def OnInit(self):
		frame = TileFrame(None, NewIdRef(), "Tile Editor")
		frame.Show()
		self.SetTopWindow(frame)
		return true

if __name__ == '__main__':
	app = TileEditApp(0)
	app.MainLoop()
