include ../Makefile.def

LIB=../fastgl.$(LIBEXT)

all: build-me

build-me: $(LIB)

$(LIB): fastgl.c
	$(BUILD)
	$(INSTALL_LIB) --install-dir ..

clean:
	$(RM) $(LIB)
