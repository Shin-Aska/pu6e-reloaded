#include <Python.h>
#include <GL/gl.h>

#define init_proc initfastgl

static PyObject *draw_poly_maptile(PyObject *self, PyObject *args) {
    int x, y;
    int ret;

    if (!PyArg_ParseTuple(args, "ii", &x, &y))
        return NULL;

	glTexCoord2f(0, 0); glVertex3f(x, y,  0);
	glTexCoord2f(1, 0); glVertex3f(x+16, y,  0);
	glTexCoord2f(1, 1); glVertex3f(x+16,  y+16,  0);
	glTexCoord2f(0, 1); glVertex3f(x, y+16,  0);

    ret = 0;
    return Py_BuildValue("i", ret);
}

#define blit_maptile(tile, x, y) { \
		float add = 16.0 / 256; \
		GLfloat ox, oy; \
		ox = tile % 16; oy = tile / 16; \
		ox = ox / 16.0; oy = oy / 16.0; \
		glTexCoord2f(ox, oy); glVertex3f(x, y,  0); \
		glTexCoord2f(ox + add, oy); glVertex3f(x+16, y,  0); \
		glTexCoord2f(ox + add, oy + add); glVertex3f(x+16,  y+16,  0); \
		glTexCoord2f(ox, oy + add); glVertex3f(x, y+16,  0); \
	}

static PyObject *draw_poly_maptile_1tex(PyObject *self, PyObject *args) {
    int x, y, tile;
    int ret;

    if (!PyArg_ParseTuple(args, "iii", &tile, &x, &y))
        return NULL;

	blit_maptile(tile, x, y);

    ret = 0;
    return Py_BuildValue("i", ret);
}

#define get_obj_item(array, index) PyList_GetItem(array, index)
#define get_int_item(array, index) ((int)PyInt_AsLong(PyList_GetItem(array, index)))

#define world_to_chunk(x, y, z) \
	if (z == 0) {            \
		scx = (x >> 7) & 0x7;  \
		scy = (y >> 7) & 0x7;  \
		cx  = (x >> 3) & 0xF;  \
		cy  = (y >> 3) & 0xF;  \
		tx  = x      & 0x7;  \
		ty  = y      & 0x7;  \
	} else {                 \
		scx = z - 1;         \
		scy = 8;             \
		cx  = (x >> 3) & 0x1F; \
		cy  = (y >> 3) & 0x1F; \
		tx  = x      & 0x7;  \
		ty  = y      & 0x7;  \
	}


static PyObject *draw_maptiles(PyObject *self, PyObject *args) {
    int x, y, wx, wy, wz;
	int scx, scy, cx, cy, tx, ty;
	int cw = 16;
	int xs, wxs;
	int stride, height;
	int schunk, chunk, t;
	PyObject *map, *chunks;

    if (!PyArg_ParseTuple(args, "iiiiiiiOO", &x, &y, &wx, &wy, &wz, &stride, &height, &map, &chunks))
        return NULL;

	/* Set initial coordinates. */
	xs = x;
	wxs = wx;
	if (wz != 0) cw *= 2;   // double number of chunks for dungeons

	while (y < height) {
		while (x < stride) {
			world_to_chunk(wx, wy, wz);   /* macro: assigns to scx, scy, cx, cy, tx, ty */
			schunk = scx + scy * 8;
			chunk = get_int_item(get_obj_item(map, schunk), cx + cy * cw);
			t = get_int_item(get_obj_item(chunks, chunk), tx + ty * 8);

			blit_maptile(t, x, y);

			x += 16;
			wx += 1;
		}

		/* Next row */
		x = xs; wx = wxs;
		y += 16;
		wy += 1;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject *draw_chunk(PyObject *self, PyObject *args) {
    int x, y, i, j;
	int stride, height;
	int t;
	PyObject *map, *chunks;
	PyObject *tiles;

    if (!PyArg_ParseTuple(args, "Oii", &tiles, &x, &y))
        return NULL;

	for (j = 0; j < 64; j+=8) {
		for (i = 0; i < 8; i++) {
			t = get_int_item(tiles, i+j);
			blit_maptile(t, x, y);
			x += 16;
		}
		x -= 128;
		y += 16;
	}

	Py_INCREF(Py_None);
	return Py_None;
}


static PyObject *draw_poly_tex(PyObject *self, PyObject *args) {
    int x, y, z, t;
    int ret;

    if (!PyArg_ParseTuple(args, "iiii", &t, &x, &y, &z))
        return NULL;

	glBindTexture(GL_TEXTURE_2D, t);
	glBegin(GL_QUADS);
		glTexCoord2f(0, 0); glVertex3f(x, y,  z);
		glTexCoord2f(1, 0); glVertex3f(x+16, y,  z);
		glTexCoord2f(1, 1); glVertex3f(x+16,  y+16,  z);
		glTexCoord2f(0, 1); glVertex3f(x, y+16,  z);
	glEnd();

    ret = 0;
    return Py_BuildValue("i", ret);
}

static PyObject *draw_object(PyObject *self, PyObject *args) {
    int x, y, t, status, wx, wy, ox, oy, stride, height;
    PyObject *ret;

    if (!PyArg_ParseTuple(args, "iiiiiiii", &t, &status, &ox, &oy, &wx, &wy, &stride, &height))
        return NULL;

    ret = Py_BuildValue("i", 0);

	// if (status & 0xF6) return ret;
	if (ox < wx) return ret;
	if (oy < wy) return ret;

	x = 16 * (ox - wx);
	if (x >= stride + 16) return ret;
	y = 16 * (oy - wy);
	if (y >= height + 16) return ret;

	glBindTexture(GL_TEXTURE_2D, t);
	glBegin(GL_QUADS);
		glTexCoord2f(0, 0); glVertex3f(x, y,  0);
		glTexCoord2f(1, 0); glVertex3f(x+16, y,  0);
		glTexCoord2f(1, 1); glVertex3f(x+16,  y+16,  0);
		glTexCoord2f(0, 1); glVertex3f(x, y+16,  0);
	glEnd();

    return ret;
}

#define tileflag(index)   ((int)PyInt_AsLong(PyTuple_GetItem(tileflag_obj, index)))
#define tile_size(tile)   ((tileflag(0x800 + tile) >> 6) & 0x3)
#define tile_height(tile) ((tileflag(0x800 + tile) >> 4) & 0x1)
#define textures(tile)    ((int)PyInt_AsLong(PyList_GET_ITEM(textures_obj, tile)))

#define blit_tex(tile, x, y, h) do {  \
	glBindTexture(GL_TEXTURE_2D, tile); \
	glBegin(GL_QUADS); \
	glTexCoord2f(0, 0); glVertex3f(x, y,  h); \
	glTexCoord2f(1, 0); glVertex3f(x+16, y,  h); \
	glTexCoord2f(1, 1); glVertex3f(x+16,  y+16,  h); \
	glTexCoord2f(0, 1); glVertex3f(x, y+16,  h); \
	glEnd(); } while (0)

static PyObject *draw_objblk(PyObject *self, PyObject *args) {
    int x, y, h, t, size, status, wx, wy, sx, sy, ox, oy, stride, height;
	PyObject *objblk;
	PyObject *textures_obj;
	PyObject *tileflag_obj;
    PyObject *ret;
	PyObject *rows, *row, *point;
	PyObject *node;
	PyObject *tile;
	int i, j, dh, o, p, index;
	int block;
	int num_points, num_rows;
	PyObject *obj;

    if (!PyArg_ParseTuple(args, "iiiiiiiiOOO", &block, &wx, &wy, &sx, &sy, &dh, &stride, &height, &objblk, &textures_obj, &tileflag_obj))
        return NULL;

	rows = PyList_GetItem(objblk, block);              // objblk[block]
	// dh is draw_height (0 or 1).  It controls the drawing direction:
	// forward (se - nw, height 0) and reverse (nw - se, height 1).
	// Draw only objects matching draw height each pass.
	/* Note: we must manually reverse (iterate backwards through) the rows and
	 * columns when drawing in reverse. */
	num_rows = PyList_GET_SIZE(rows);

	for (j = 0; j < num_rows; j++) {
		if (dh == 0) { index = j; }
		else         { index = num_rows - j - 1; }

		node = PyList_GetItem(rows, index);
		oy = (int)PyInt_AS_LONG(PyList_GetItem(node, 0));

		if (oy < wy) {
			/* If we're drawing from bottom to top, stop parsing this block
			 * once we go off the top of the screen.  From top to bottom
			 * we just skip to the next object. */
			if (dh) continue; else break;
		}

		y = sy + 16 * (oy - wy);
		if (y >= height + 16) {
			/* See comments above; this test is reversed.  This doesn't buy
			 * us any time, really, because drawing dominates anyway. */
			if (!dh) continue; else break;
		}

		row = PyList_GetItem(node, 1);
		num_points = PyList_GET_SIZE(row);

		for (p = 0; p < num_points; p++) {
			// Iterate forward or reverse.  Could do it mathematically to avoid the 'if'.
			int pindex, num_objs;
			if (dh == 0) { pindex = p; }
			else         { pindex = num_points - p - 1; }

			node = PyList_GetItem(row, pindex);
			ox = (int)PyInt_AS_LONG(PyList_GetItem(node, 0));

			if (ox < wx) continue;
			x = sx + 16 * (ox - wx);
			if (x >= stride + 16) continue;

			point = PyList_GetItem(node, 1);

			num_objs = PyList_GET_SIZE(point);
			for (o = 0; o < num_objs; o++) {
				obj = PyList_GetItem(point, o);   // for obj in objblk[block]
				//t = (int)PyInt_AS_LONG(PyList_GetItem(obj, 3));
				//tile = PyDict_GetItemString(*((PyObject **) ((char *)obj + obj->ob_type->tp_dictoffset)), "tile");
				tile = PyObject_GetAttrString(obj, "tile");
				t = (int)PyInt_AsLong(tile);
				Py_DECREF(tile);

				/* I see no performance gain from moving the BindTexture out of the loop. */
				h = tile_height(t);
				if (dh == h) blit_tex(textures(t), x, y, h);  // It's safe to use textures(t) in the macro.

				size = tile_size(t);
				if (size & 2) {   // Width 2: lower left
					t -= 1;
					if (x - 16 < stride && y < height && x - 16 >= 0) {
						h = tile_height(t);
						if (dh == h) blit_tex(textures(t), x - 16, y, h);
					}
				}
				if (size & 1) {   // Height 2: upper right
					t -= 1;
					if (x < stride && y - 16 < height && y - 16 >= 0) {
						h = tile_height(t);
						if (dh == h) blit_tex(textures(t), x, y - 16, h);
					}
					if (size & 2) {  // Width 2: upper left
						t -= 1;
						if (x - 16 < stride && y - 16 < height && x - 16 >= 0 && y - 16 >= 0) {
							h = tile_height(t);
							if (dh == h) blit_tex(textures(t), x - 16, y - 16, h);
						}
					}
				}
			}
		}
	}

    ret = Py_BuildValue("i", 0);
	return ret;
}

static PyObject *indexed_to_rgba(PyObject *self, PyObject *args) {
	unsigned char *data, *pal;
	unsigned char *out, *pout;
	PyObject *ret;
	int size, palsize, outsize;
	int p, i;
	int paletted_tile = 0;

    if (!PyArg_ParseTuple(args, "t#t#", &data, &size, &pal, &palsize)) return NULL;

	outsize = size * 4 * sizeof(unsigned char);
	out = (unsigned char *)malloc(outsize);
	pout = out;

	for (i = 0; i < size; i++) {
		p = (int)(*data);
		*pout++ = pal[p*3];
		*pout++ = pal[p*3+1];
		*pout++ = pal[p*3+2];
		if (p == 255) {
			*pout++ = 0;
		} else {
			*pout++ = 255;
		}
		if (p >= 0xE0 && p <= 0xFB) {
			paletted_tile = 1;
		}
		data++;
	}

	ret = Py_BuildValue("s#i", out, outsize, paletted_tile);
	free(out);
	return ret;
}

static PyObject *indexed_to_rgb(PyObject *self, PyObject *args) {
	unsigned char *data, *pal;
	unsigned char *out, *pout;
	PyObject *ret;
	int size, palsize, outsize;
	int p, i;

    if (!PyArg_ParseTuple(args, "t#t#", &data, &size, &pal, &palsize)) return NULL;

	outsize = size * 3 * sizeof(unsigned char);
	out = (unsigned char *)malloc(outsize);
	pout = out;

	for (i = 0; i < size; i++) {
		p = (int)(*data);
		*pout++ = pal[p*3];
		*pout++ = pal[p*3+1];
		*pout++ = pal[p*3+2];
		data++;
	}

	ret = Py_BuildValue("s#", out, outsize);
	free(out);
	return ret;
}

/* This is the PyOpenGL glTexSubImage2D wrapper, modified to use the
 * buffer interface rather than require a string.  A simple change
 * to the const void * typemap would have the same effect, but would
 * require a full recompile of PyOpenGL... */
/* For example:
 * %typemap( python, in) const void *
 * { int len;
 *   if (PyObject_AsReadBuffer($source, (void **)&$target, &len) < 0)
 *		return NULL;
 * }
 * */

#define SWIG_fail goto fail
static PyObject *_wrap_glTexSubImage2D(PyObject *self, PyObject *args) {
    PyObject *resultobj;
    GLenum arg1 ;
    GLint arg2 ;
    GLint arg3 ;
    GLint arg4 ;
    GLsizei arg5 ;
    GLsizei arg6 ;
    GLenum arg7 ;
    GLenum arg8 ;
    void *arg9 = (void *) 0 ;
    PyObject * obj0  = 0 ;
    PyObject * obj6  = 0 ;
    PyObject * obj7  = 0 ;
    PyObject * obj8  = 0 ;

    if(!PyArg_ParseTuple(args,(char *)"OiiiiiOOO:glTexSubImage2D",&obj0,&arg2,&arg3,&arg4,&arg5,&arg6,&obj6,&obj7,&obj8)) goto fail;
    arg1 = (GLenum) PyInt_AsLong(obj0);
    if (PyErr_Occurred()) SWIG_fail;
    arg7 = (GLenum) PyInt_AsLong(obj6);
    if (PyErr_Occurred()) SWIG_fail;
    arg8 = (GLenum) PyInt_AsLong(obj7);
    if (PyErr_Occurred()) SWIG_fail;
    {
        int len;
        if (obj8 == Py_None) arg9 = NULL; else
        {
			if (PyObject_AsReadBuffer(obj8, (const void **)&arg9, &len) < 0)
				return NULL;
        }
    }
    glTexSubImage2D(arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,(void const *)arg9);

    Py_INCREF(Py_None); resultobj = Py_None;
    return resultobj;
    fail:
    return NULL;
}

static PyMethodDef Methods[] = {
    {"draw_poly_maptile",  draw_poly_maptile, METH_VARARGS,
     "draw maptile as GL polygon" },
    {"draw_poly_maptile_1tex",  draw_poly_maptile_1tex, METH_VARARGS,
     "draw maptile as GL polygon using map texture" },
    {"draw_maptiles",  draw_maptiles, METH_VARARGS,
     "draw square region of map tiles" },
    {"draw_chunk",  draw_chunk, METH_VARARGS,
     "draw 8x8 chunk" },
    {"draw_poly_tex",  draw_poly_tex, METH_VARARGS,
     "bind texture and draw textured polygon" },
    {"draw_object",  draw_object, METH_VARARGS,
     "draw object" },
    {"draw_objblk",  draw_objblk, METH_VARARGS,
     "draw objblk" },
    {"indexed_to_rgb",  indexed_to_rgb, METH_VARARGS,
     "convert paletted image to rgb (no transparency)" },
    {"indexed_to_rgba",  indexed_to_rgba, METH_VARARGS,
     "convert paletted image to rgba" },
    {"glTexSubImage2D",  _wrap_glTexSubImage2D, METH_VARARGS,
     "glTexSubImage2D, using the buffer interface" },
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

void init_proc(void) {
    (void)Py_InitModule("fastgl", Methods);
}
