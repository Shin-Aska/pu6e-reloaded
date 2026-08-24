%module lzw
%{
#include "lzw.h"
%}

%include "cstring.i"

%cstring_input_binary(char *buf, int length)

int is_valid_lzw_buffer(char *buf, int length);
int get_uncompressed_size_buffer(char *buf, int length);

%{
PyObject *_lzw_decompress_buffer(char *buf, int length)
{
	char *dest;
	int dlen;
	PyObject *ret;

	if (!is_valid_lzw_buffer(buf, length)) goto fail;
	dlen = get_uncompressed_size_buffer(buf, length);
	if (dlen < 0 || length < 4) goto fail;
	length -= 4; buf += 4;  /* lzw_decompress_buffer expects start of buffer, after file size */

	dest = (char *)PyMem_Malloc(dlen);
	if (dest == NULL) return PyErr_NoMemory();
	lzw_decompress_buffer(buf, length, dest, dlen); /* No error checking performed! */
	ret = PyString_FromStringAndSize(dest, dlen); /* copy -- very inefficient */
	PyMem_Free(dest);
	return ret;

fail:
	Py_INCREF(Py_None);
	return Py_None;
}
%}

%name(decompress_buffer) PyObject *_lzw_decompress_buffer(char *buf, int length);
/* DOC(lzw_decompress_buffer, "lzw_decompress_buffer(string) -> string") */
