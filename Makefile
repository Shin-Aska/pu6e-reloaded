include Makefile.def

all: build-u6decode build-lzw build-fastgl

clean:
	$(MAKE) -C lzw clean
	$(MAKE) -C fastgl clean
	$(MAKE) -C u6decode clean
	$(RM) *.pyc U6/*.pyc

build-u6decode:
	$(MAKE) -C u6decode

build-lzw:
	$(MAKE) -C lzw

build-fastgl:
	$(MAKE) -C fastgl

py2exe:
	python setup-exe.py py2exe --excludes=OpenGL
