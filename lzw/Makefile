include ../Makefile.def

LIB=../_lzw.$(LIBEXT)
PY=../U6/lzw.py

all: build-lzw

build-lzw: $(LIB) $(PY)

$(LIB): lzw_wrap.c
	$(BUILD)
	$(INSTALL_LIB) --install-dir ..

$(PY): lzw.py
	$(INSTALL_SCR) --install-dir ../U6

lzw_wrap.c: lzw.i
	$(SWIG) $<

lzw.py: lzw.i
	$(SWIG) $<

clean:
	$(RM) $(LIB) $(PY) lzw_wrap.c lzw.py
